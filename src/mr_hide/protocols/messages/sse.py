"""Bounded, ordered Anthropic Messages SSE transformation."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from typing import Any

from mr_hide.policy import ContentKind
from mr_hide.protocols.messages.json_body import (
    MAX_JSON_BYTES,
    MessagesTransformError,
    TextTransform,
    _transform_json_tree,
    _validate_depth,
    dump_event_json,
    load_event_json,
    transform_event_document,
)

MAX_SSE_BYTES = 32 * 1024 * 1024
_MAX_BLOCK_INDEX = 1_000_000
_FRAME_BOUNDARY = re.compile(br"\r?\n\r?\n")
_TRANSFORMED_TYPES = {"message_start", "content_block_start", "error"}
_STREAM_TYPES = {"content_block_delta", "content_block_stop"}


@dataclass(slots=True)
class _Frame:
    raw: bytes
    document: dict[str, Any] | None
    newline: str
    non_data_lines: tuple[str, ...]


@dataclass(slots=True)
class _PendingBlock:
    block_type: str
    delta_indices: list[int]


async def transform_sse_stream(
    chunks: AsyncIterable[bytes],
    transform: TextTransform,
) -> AsyncIterator[bytes]:
    payload = bytearray()
    async for chunk in chunks:
        if not isinstance(chunk, bytes):
            raise MessagesTransformError("messages-sse-invalid")
        payload.extend(chunk)
        if len(payload) > MAX_SSE_BYTES:
            raise MessagesTransformError("messages-sse-too-large")
    yield transform_sse_bytes(bytes(payload), transform)


def transform_sse_bytes(payload: bytes, transform: TextTransform) -> bytes:
    if not payload or len(payload) > MAX_SSE_BYTES:
        raise MessagesTransformError("messages-sse-size-invalid")
    frames = _parse_frames(payload)
    _transform_content_blocks(frames, transform)
    for frame in frames:
        document = frame.document
        if document is not None and document.get("type") in _TRANSFORMED_TYPES:
            transform_event_document(document, transform)
    result = b"".join(_render_frame(frame) for frame in frames)
    if len(result) > MAX_SSE_BYTES:
        raise MessagesTransformError("messages-sse-too-large")
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
        raise MessagesTransformError("messages-sse-event-too-large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise MessagesTransformError("messages-sse-invalid") from None
    newline = "\r\n" if "\r\n" in text else "\n"
    data_values: list[str] = []
    non_data: list[str] = []
    event_names: list[str] = []
    for line in text.splitlines():
        if line == "data":
            data_values.append("")
        elif line.startswith("data:"):
            value = line[5:]
            data_values.append(value[1:] if value.startswith(" ") else value)
        elif line.startswith("event:"):
            value = line[6:]
            event_names.append(value[1:] if value.startswith(" ") else value)
            non_data.append(line)
        elif line:
            non_data.append(line)
    if not data_values:
        return _Frame(raw, None, newline, tuple(non_data))
    document = load_event_json("\n".join(data_values).encode("utf-8"))
    event_type = document.get("type")
    if not isinstance(event_type, str):
        raise MessagesTransformError("messages-sse-event-invalid")
    if len(event_names) > 1 or (event_names and event_names[0] != event_type):
        raise MessagesTransformError("messages-sse-event-mismatch")
    known = event_type in _TRANSFORMED_TYPES or event_type in _STREAM_TYPES
    return _Frame(raw, document if known else None, newline, tuple(non_data))


def _transform_content_blocks(frames: list[_Frame], transform: TextTransform) -> None:
    pending: dict[int, _PendingBlock] = {}
    for frame_index, frame in enumerate(frames):
        document = frame.document
        if document is None:
            continue
        event_type = document.get("type")
        if event_type == "content_block_start":
            index = _block_index(document)
            block = document.get("content_block")
            if not isinstance(block, dict) or not isinstance(block.get("type"), str):
                raise MessagesTransformError("messages-sse-event-invalid")
            if index in pending:
                raise MessagesTransformError("messages-sse-block-order-invalid")
            pending[index] = _PendingBlock(str(block["type"]), [])
        elif event_type == "content_block_delta":
            index = _block_index(document)
            active = pending.get(index)
            delta = document.get("delta")
            if active is None or not isinstance(delta, dict):
                raise MessagesTransformError("messages-sse-block-order-invalid")
            delta_type = delta.get("type")
            expected = {
                "text": "text_delta",
                "tool_use": "input_json_delta",
            }.get(active.block_type)
            if expected is not None:
                if delta_type != expected:
                    raise MessagesTransformError("messages-sse-delta-invalid")
                field = "text" if expected == "text_delta" else "partial_json"
                if not isinstance(delta.get(field), str):
                    raise MessagesTransformError("messages-sse-delta-invalid")
                active.delta_indices.append(frame_index)
        elif event_type == "content_block_stop":
            index = _block_index(document)
            active = pending.pop(index, None)
            if active is None:
                raise MessagesTransformError("messages-sse-block-order-invalid")
            _complete_block(frames, active, transform)
    if pending:
        raise MessagesTransformError("messages-sse-incomplete-block")


def _complete_block(
    frames: list[_Frame],
    block: _PendingBlock,
    transform: TextTransform,
) -> None:
    if block.block_type not in {"text", "tool_use"}:
        return
    if not block.delta_indices:
        raise MessagesTransformError("messages-sse-incomplete-delta")
    field = "text" if block.block_type == "text" else "partial_json"
    combined = "".join(_delta_value(frames[index], field) for index in block.delta_indices)
    if block.block_type == "text":
        transformed = _call_transform(combined, ContentKind.CONVERSATION, transform)
    else:
        transformed = _transform_tool_json(combined, transform)
    for position, index in enumerate(block.delta_indices):
        document = frames[index].document
        if document is None or not isinstance(document.get("delta"), dict):
            raise MessagesTransformError("messages-sse-delta-invalid")
        document["delta"][field] = transformed if position == 0 else ""


def _transform_tool_json(payload: str, transform: TextTransform) -> str:
    try:
        encoded = payload.encode("utf-8")
    except UnicodeEncodeError:
        raise MessagesTransformError("messages-tool-input-invalid") from None
    if len(encoded) > MAX_JSON_BYTES:
        raise MessagesTransformError("messages-json-size-invalid")
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_unique_tool_object,
            parse_constant=_invalid_tool_constant,
        )
    except MessagesTransformError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError):
        raise MessagesTransformError("messages-tool-input-invalid") from None
    if not isinstance(value, dict):
        raise MessagesTransformError("messages-tool-input-invalid")
    _validate_depth(value)
    transformed = _transform_json_tree(value, ContentKind.TOOL_ARGUMENT, transform)
    try:
        result = json.dumps(
            transformed,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        raise MessagesTransformError("messages-tool-input-invalid") from None
    try:
        result_size = len(result.encode("utf-8"))
    except UnicodeEncodeError:
        raise MessagesTransformError("messages-tool-input-invalid") from None
    if result_size > MAX_JSON_BYTES:
        raise MessagesTransformError("messages-json-size-invalid")
    return result


def _unique_tool_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MessagesTransformError("messages-json-duplicate-key")
        result[key] = value
    return result


def _invalid_tool_constant(_value: str) -> object:
    raise MessagesTransformError("messages-tool-input-invalid")


def _block_index(document: dict[str, Any]) -> int:
    value = document.get("index")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _MAX_BLOCK_INDEX:
        raise MessagesTransformError("messages-sse-index-invalid")
    return value


def _delta_value(frame: _Frame, field: str) -> str:
    document = frame.document
    delta = None if document is None else document.get("delta")
    value = None if not isinstance(delta, dict) else delta.get(field)
    if not isinstance(value, str):
        raise MessagesTransformError("messages-sse-delta-invalid")
    return value


def _call_transform(text: str, kind: ContentKind, transform: TextTransform) -> str:
    try:
        result = transform(text, kind)
    except MessagesTransformError:
        raise
    except Exception:
        raise MessagesTransformError("messages-text-transform-failed") from None
    if not isinstance(result, str):
        raise MessagesTransformError("messages-text-transform-failed")
    return result


def _render_frame(frame: _Frame) -> bytes:
    if frame.document is None:
        return frame.raw
    lines = [*frame.non_data_lines, f"data: {dump_event_json(frame.document).decode('utf-8')}"]
    return (frame.newline.join(lines) + frame.newline * 2).encode("utf-8")
