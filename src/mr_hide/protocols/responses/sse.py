"""Bounded, ordered OpenAI Responses SSE transformation."""

from __future__ import annotations

import re
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from typing import Any

from mr_hide.protocols.responses.json_body import (
    MAX_JSON_BYTES,
    ResponsesTransformError,
    TextTransform,
    _dump,
    _load_json,
    _validate_depth,
    transform_event_document,
)

MAX_SSE_BYTES = 32 * 1024 * 1024
_FRAME_BOUNDARY = re.compile(br"\r?\n\r?\n")


@dataclass(slots=True)
class _Frame:
    raw: bytes
    document: dict[str, Any] | None
    newline: str
    non_data_lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DeltaSpec:
    done_type: str
    delta_field: str
    done_field: str


_DELTA_SPECS = {
    "response.output_text.delta": _DeltaSpec(
        "response.output_text.done",
        "delta",
        "text",
    ),
    "response.refusal.delta": _DeltaSpec(
        "response.refusal.done",
        "delta",
        "refusal",
    ),
    "response.function_call_arguments.delta": _DeltaSpec(
        "response.function_call_arguments.done",
        "delta",
        "arguments",
    ),
    "response.mcp_call_arguments.delta": _DeltaSpec(
        "response.mcp_call_arguments.done",
        "delta",
        "arguments",
    ),
    "response.custom_tool_call_input.delta": _DeltaSpec(
        "response.custom_tool_call_input.done",
        "delta",
        "input",
    ),
    "response.reasoning_summary_text.delta": _DeltaSpec(
        "response.reasoning_summary_text.done",
        "delta",
        "text",
    ),
    "response.reasoning_text.delta": _DeltaSpec(
        "response.reasoning_text.done",
        "delta",
        "text",
    ),
}
_DONE_TO_DELTA = {spec.done_type: delta for delta, spec in _DELTA_SPECS.items()}
_DIRECT_EVENT_TYPES = {
    "response.created",
    "response.queued",
    "response.in_progress",
    "response.completed",
    "response.failed",
    "response.incomplete",
    "response.output_item.added",
    "response.output_item.done",
    "response.content_part.added",
    "response.content_part.done",
    "response.reasoning_summary_part.added",
    "response.reasoning_summary_part.done",
    "error",
}


async def transform_sse_stream(
    chunks: AsyncIterable[bytes],
    transform: TextTransform,
) -> AsyncIterator[bytes]:
    """Buffer one bounded stream and emit only after complete safe transformation."""

    payload = bytearray()
    async for chunk in chunks:
        if not isinstance(chunk, bytes):
            raise ResponsesTransformError("responses-sse-invalid")
        payload.extend(chunk)
        if len(payload) > MAX_SSE_BYTES:
            raise ResponsesTransformError("responses-sse-too-large")
    yield transform_sse_bytes(bytes(payload), transform)


def transform_sse_bytes(payload: bytes, transform: TextTransform) -> bytes:
    if not payload or len(payload) > MAX_SSE_BYTES:
        raise ResponsesTransformError("responses-sse-size-invalid")
    frames = _parse_frames(payload)
    _transform_delta_groups(frames, transform)
    for frame in frames:
        document = frame.document
        if document is None:
            continue
        event_type = document.get("type")
        if event_type in _DIRECT_EVENT_TYPES:
            transform_event_document(document, transform)
    result = b"".join(_render_frame(frame) for frame in frames)
    if len(result) > MAX_SSE_BYTES:
        raise ResponsesTransformError("responses-sse-too-large")
    return result


def _parse_frames(payload: bytes) -> list[_Frame]:
    frames: list[_Frame] = []
    offset = 0
    for boundary in _FRAME_BOUNDARY.finditer(payload):
        end = boundary.end()
        frames.append(_parse_frame(payload[offset:end]))
        offset = end
    if offset < len(payload):
        frames.append(_parse_frame(payload[offset:]))
    return frames


def _parse_frame(raw: bytes) -> _Frame:
    if len(raw) > MAX_JSON_BYTES:
        raise ResponsesTransformError("responses-sse-event-too-large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ResponsesTransformError("responses-sse-invalid") from None
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    data_values: list[str] = []
    non_data: list[str] = []
    for line in lines:
        if line == "data":
            data_values.append("")
        elif line.startswith("data:"):
            value = line[5:]
            data_values.append(value[1:] if value.startswith(" ") else value)
        elif line:
            non_data.append(line)
    if not data_values:
        return _Frame(raw, None, newline, tuple(non_data))
    data = "\n".join(data_values)
    if data == "[DONE]":
        return _Frame(raw, None, newline, tuple(non_data))
    document = _load_json(data, "responses-sse-json-invalid")
    if not isinstance(document, dict):
        raise ResponsesTransformError("responses-sse-json-invalid")
    _validate_depth(document)
    event_type = document.get("type")
    if not isinstance(event_type, str):
        raise ResponsesTransformError("responses-sse-event-invalid")
    known = (
        event_type in _DIRECT_EVENT_TYPES
        or event_type in _DELTA_SPECS
        or event_type in _DONE_TO_DELTA
    )
    return _Frame(raw, document if known else None, newline, tuple(non_data))


def _transform_delta_groups(frames: list[_Frame], transform: TextTransform) -> None:
    pending: dict[tuple[object, ...], list[int]] = {}
    for index, frame in enumerate(frames):
        document = frame.document
        if document is None:
            continue
        event_type = document.get("type")
        if event_type in _DELTA_SPECS:
            spec = _DELTA_SPECS[event_type]
            value = document.get(spec.delta_field)
            if not isinstance(value, str):
                raise ResponsesTransformError("responses-sse-event-invalid")
            pending.setdefault(_event_key(document, event_type), []).append(index)
        elif event_type in _DONE_TO_DELTA:
            delta_type = _DONE_TO_DELTA[event_type]
            spec = _DELTA_SPECS[delta_type]
            key = _event_key(document, delta_type)
            indices = pending.pop(key, [])
            done_value = document.get(spec.done_field)
            if not isinstance(done_value, str):
                raise ResponsesTransformError("responses-sse-event-invalid")
            if indices:
                combined = "".join(
                    _required_delta(frames[item].document, spec.delta_field)
                    for item in indices
                )
                if combined != done_value:
                    raise ResponsesTransformError("responses-sse-delta-mismatch")
            transform_event_document(document, transform)
            transformed = document[spec.done_field]
            if not isinstance(transformed, str):
                raise ResponsesTransformError("responses-sse-event-invalid")
            for position, item in enumerate(indices):
                delta_document = frames[item].document
                if delta_document is None:
                    raise ResponsesTransformError("responses-sse-event-invalid")
                delta_document[spec.delta_field] = transformed if position == 0 else ""
    if pending:
        raise ResponsesTransformError("responses-sse-incomplete-delta")


def _event_key(document: dict[str, Any], delta_type: str) -> tuple[object, ...]:
    return (
        delta_type,
        document.get("item_id"),
        document.get("output_index"),
        document.get("content_index"),
        document.get("summary_index"),
    )


def _required_delta(document: dict[str, Any] | None, field: str) -> str:
    value = None if document is None else document.get(field)
    if not isinstance(value, str):
        raise ResponsesTransformError("responses-sse-event-invalid")
    return value


def _render_frame(frame: _Frame) -> bytes:
    if frame.document is None:
        return frame.raw
    lines = [*frame.non_data_lines, f"data: {_dump(frame.document).decode('utf-8')}"]
    return (frame.newline.join(lines) + frame.newline * 2).encode("utf-8")
