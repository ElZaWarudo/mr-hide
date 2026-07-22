"""Explicit, bounded OpenAI Responses JSON field transformations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mr_hide.policy import ContentKind

MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64

TextTransform = Callable[[str, ContentKind], str]


class ResponsesTransformError(RuntimeError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def transform_request_json(payload: bytes, transform: TextTransform) -> bytes:
    document = _load_outer(payload)
    _transform_request(document, transform)
    return _dump(document)


def transform_response_json(payload: bytes, transform: TextTransform) -> bytes:
    document = _load_outer(payload)
    _transform_response(document, transform)
    return _dump(document)


def transform_event_document(document: dict[str, Any], transform: TextTransform) -> None:
    """Transform one complete Responses SSE event document in place."""

    event_type = document.get("type")
    if not isinstance(event_type, str):
        raise ResponsesTransformError("responses-event-invalid")
    if event_type in {
        "response.created",
        "response.queued",
        "response.in_progress",
        "response.completed",
        "response.failed",
        "response.incomplete",
    }:
        response = document.get("response")
        if not isinstance(response, dict):
            raise ResponsesTransformError("responses-event-invalid")
        _transform_response(response, transform)
    elif event_type == "response.output_text.done":
        _transform_required_string(document, "text", ContentKind.CONVERSATION, transform)
    elif event_type == "response.refusal.done":
        _transform_required_string(document, "refusal", ContentKind.CONVERSATION, transform)
    elif event_type in {
        "response.reasoning_summary_text.done",
        "response.reasoning_text.done",
    }:
        _transform_required_string(document, "text", ContentKind.CONVERSATION, transform)
    elif event_type in {
        "response.function_call_arguments.done",
        "response.mcp_call_arguments.done",
    }:
        _transform_inner_json_field(document, "arguments", ContentKind.TOOL_ARGUMENT, transform)
    elif event_type == "response.custom_tool_call_input.done":
        _transform_required_string(document, "input", ContentKind.TOOL_ARGUMENT, transform)
    elif event_type == "error":
        _transform_optional_string(document, "message", ContentKind.CONVERSATION, transform)
    elif event_type in {"response.output_item.added", "response.output_item.done"}:
        item = document.get("item")
        _transform_item(
            item,
            transform,
            allow_incomplete=event_type == "response.output_item.added",
        )
    elif event_type in {
        "response.content_part.added",
        "response.content_part.done",
        "response.reasoning_summary_part.added",
        "response.reasoning_summary_part.done",
    }:
        part = document.get("part")
        if not isinstance(part, dict):
            raise ResponsesTransformError("responses-event-invalid")
        part_type = part.get("type")
        if part_type in {"output_text", "summary_text", "reasoning_text"}:
            _transform_required_string(part, "text", ContentKind.CONVERSATION, transform)
        elif part_type == "refusal":
            _transform_required_string(part, "refusal", ContentKind.CONVERSATION, transform)


def _load_outer(payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_JSON_BYTES:
        raise ResponsesTransformError("responses-json-size-invalid")
    document = _load_json(payload, "responses-json-invalid")
    if not isinstance(document, dict):
        raise ResponsesTransformError("responses-json-invalid")
    _validate_depth(document)
    return document


def _load_json(payload: bytes | str, reason: str) -> object:
    try:
        return json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except ResponsesTransformError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError):
        raise ResponsesTransformError(reason) from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResponsesTransformError("responses-json-duplicate-key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise ResponsesTransformError("responses-json-invalid")


def _validate_depth(value: object, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ResponsesTransformError("responses-json-too-deep")
    if isinstance(value, dict):
        for child in value.values():
            _validate_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_depth(child, depth + 1)


def _dump(document: object) -> bytes:
    try:
        payload = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ResponsesTransformError("responses-json-invalid") from None
    if len(payload) > MAX_JSON_BYTES:
        raise ResponsesTransformError("responses-json-size-invalid")
    return payload


def _transform_request(document: dict[str, Any], transform: TextTransform) -> None:
    _transform_optional_text_or_items(document, "instructions", transform)
    _transform_optional_text_or_items(document, "input", transform)
    tools = document.get("tools")
    if tools is not None:
        if not isinstance(tools, list):
            raise ResponsesTransformError("responses-tools-invalid")
        transformed_tools: list[object] = []
        for tool in tools:
            if not isinstance(tool, dict):
                raise ResponsesTransformError("responses-tools-invalid")
            transformed_tools.append(
                _transform_recursive(tool, ContentKind.TOOL_DEFINITION, transform)
            )
        document["tools"] = transformed_tools
    prompt = document.get("prompt")
    if prompt is not None:
        if not isinstance(prompt, dict):
            raise ResponsesTransformError("responses-prompt-invalid")
        variables = prompt.get("variables")
        if variables is not None:
            prompt["variables"] = _transform_recursive(
                variables,
                ContentKind.CONVERSATION,
                transform,
                transform_keys=False,
            )


def _transform_response(document: dict[str, Any], transform: TextTransform) -> None:
    _transform_optional_text_or_items(document, "instructions", transform)
    output = document.get("output")
    if output is not None:
        if not isinstance(output, list):
            raise ResponsesTransformError("responses-output-invalid")
        for item in output:
            _transform_item(item, transform)
    error = document.get("error")
    if error is not None:
        if not isinstance(error, dict):
            raise ResponsesTransformError("responses-error-invalid")
        _transform_optional_string(error, "message", ContentKind.CONVERSATION, transform)


def _transform_optional_text_or_items(
    document: dict[str, Any],
    field: str,
    transform: TextTransform,
) -> None:
    value = document.get(field)
    if value is None:
        return
    if isinstance(value, str):
        document[field] = _apply(transform, value, ContentKind.CONVERSATION)
        return
    if not isinstance(value, list):
        raise ResponsesTransformError("responses-content-invalid")
    for item in value:
        _transform_item(item, transform)


def _transform_item(
    value: object,
    transform: TextTransform,
    *,
    allow_incomplete: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise ResponsesTransformError("responses-item-invalid")
    item_type = value.get("type")
    if item_type in {None, "message"} and "content" in value:
        _transform_content(value, transform, ContentKind.CONVERSATION)
    elif item_type == "function_call_output":
        _transform_output_value(value, "output", ContentKind.TOOL_RESULT, transform)
    elif item_type in {"function_call", "mcp_call"}:
        arguments = value.get("arguments")
        if not (allow_incomplete and arguments == ""):
            _transform_inner_json_field(
                value,
                "arguments",
                ContentKind.TOOL_ARGUMENT,
                transform,
            )
        _transform_optional_string(value, "name", ContentKind.TOOL_DEFINITION, transform)
    elif item_type == "custom_tool_call":
        _transform_required_string(value, "input", ContentKind.TOOL_ARGUMENT, transform)
        _transform_optional_string(value, "name", ContentKind.TOOL_DEFINITION, transform)
    elif item_type == "reasoning":
        _transform_reasoning(value, transform)
    elif item_type is not None and not isinstance(item_type, str):
        raise ResponsesTransformError("responses-item-invalid")


def _transform_content(
    document: dict[str, Any],
    transform: TextTransform,
    kind: ContentKind,
) -> None:
    content = document.get("content")
    if isinstance(content, str):
        document["content"] = _apply(transform, content, kind)
        return
    if not isinstance(content, list):
        raise ResponsesTransformError("responses-content-invalid")
    for part in content:
        if not isinstance(part, dict):
            raise ResponsesTransformError("responses-content-invalid")
        part_type = part.get("type")
        if part_type in {"input_text", "output_text", "summary_text", "reasoning_text"}:
            _transform_required_string(part, "text", kind, transform)
        elif part_type == "refusal":
            _transform_required_string(part, "refusal", kind, transform)


def _transform_reasoning(document: dict[str, Any], transform: TextTransform) -> None:
    for field in ("summary", "content"):
        parts = document.get(field)
        if parts is None:
            continue
        if not isinstance(parts, list):
            raise ResponsesTransformError("responses-content-invalid")
        for part in parts:
            if isinstance(part, dict) and part.get("type") in {"summary_text", "reasoning_text"}:
                _transform_required_string(part, "text", ContentKind.CONVERSATION, transform)


def _transform_output_value(
    document: dict[str, Any],
    field: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    value = document.get(field)
    if isinstance(value, str):
        document[field] = _apply(transform, value, kind)
    elif isinstance(value, list):
        document[field] = _transform_recursive(value, kind, transform, transform_keys=False)
    else:
        raise ResponsesTransformError("responses-tool-output-invalid")


def _transform_inner_json_field(
    document: dict[str, Any],
    field: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    value = document.get(field)
    if not isinstance(value, str):
        raise ResponsesTransformError("responses-tool-arguments-invalid")
    if len(value.encode("utf-8")) > MAX_JSON_BYTES:
        raise ResponsesTransformError("responses-json-size-invalid")
    inner = _load_json(value, "responses-tool-arguments-invalid")
    if not isinstance(inner, dict):
        raise ResponsesTransformError("responses-tool-arguments-invalid")
    _validate_depth(inner)
    transformed = _transform_recursive(inner, kind, transform)
    document[field] = _dump(transformed).decode("utf-8")


def _transform_recursive(
    value: object,
    kind: ContentKind,
    transform: TextTransform,
    *,
    transform_keys: bool = True,
) -> object:
    if isinstance(value, str):
        return _apply(transform, value, kind)
    if isinstance(value, list):
        return [
            _transform_recursive(item, kind, transform, transform_keys=transform_keys)
            for item in value
        ]
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, child in value.items():
            transformed_key = _apply(transform, key, kind) if transform_keys else key
            if transformed_key in result:
                raise ResponsesTransformError("responses-transformed-key-collision")
            result[transformed_key] = _transform_recursive(
                child,
                kind,
                transform,
                transform_keys=transform_keys,
            )
        return result
    return value


def _transform_required_string(
    document: dict[str, Any],
    field: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    value = document.get(field)
    if not isinstance(value, str):
        raise ResponsesTransformError("responses-content-invalid")
    document[field] = _apply(transform, value, kind)


def _transform_optional_string(
    document: dict[str, Any],
    field: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    value = document.get(field)
    if value is None:
        return
    if not isinstance(value, str):
        raise ResponsesTransformError("responses-content-invalid")
    document[field] = _apply(transform, value, kind)


def _apply(transform: TextTransform, value: str, kind: ContentKind) -> str:
    try:
        transformed = transform(value, kind)
    except ResponsesTransformError:
        raise
    except Exception:
        raise ResponsesTransformError("responses-text-transform-failed") from None
    if not isinstance(transformed, str):
        raise ResponsesTransformError("responses-text-transform-failed")
    return transformed
