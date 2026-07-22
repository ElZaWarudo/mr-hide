"""Explicit, bounded Anthropic Messages JSON field transformations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mr_hide.policy import ContentKind

MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
TextTransform = Callable[[str, ContentKind], str]


class MessagesTransformError(RuntimeError):
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
    event_type = document.get("type")
    if not isinstance(event_type, str):
        raise MessagesTransformError("messages-event-invalid")
    if event_type == "message_start":
        message = document.get("message")
        if not isinstance(message, dict):
            raise MessagesTransformError("messages-event-invalid")
        _transform_response(message, transform)
    elif event_type == "content_block_start":
        block = document.get("content_block")
        if not isinstance(block, dict):
            raise MessagesTransformError("messages-event-invalid")
        _transform_output_block(block, transform, allow_incomplete=True)
    elif event_type == "error":
        error = document.get("error")
        if not isinstance(error, dict):
            raise MessagesTransformError("messages-event-invalid")
        _transform_optional_string(error, "message", ContentKind.CONVERSATION, transform)


def load_event_json(payload: bytes) -> dict[str, Any]:
    value = _load_json(payload, "messages-sse-json-invalid")
    if not isinstance(value, dict):
        raise MessagesTransformError("messages-sse-json-invalid")
    _validate_depth(value)
    return value


def dump_event_json(document: dict[str, Any]) -> bytes:
    return _dump(document)


def _load_outer(payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_JSON_BYTES:
        raise MessagesTransformError("messages-json-size-invalid")
    value = _load_json(payload, "messages-json-invalid")
    if not isinstance(value, dict):
        raise MessagesTransformError("messages-json-invalid")
    _validate_depth(value)
    return value


def _load_json(payload: bytes | str, reason: str) -> object:
    try:
        return json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except MessagesTransformError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError):
        raise MessagesTransformError(reason) from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MessagesTransformError("messages-json-duplicate-key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise MessagesTransformError("messages-json-invalid")


def _validate_depth(value: object, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise MessagesTransformError("messages-json-too-deep")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise MessagesTransformError("messages-json-invalid")
            _validate_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_depth(child, depth + 1)


def _dump(document: dict[str, Any]) -> bytes:
    try:
        payload = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
        raise MessagesTransformError("messages-json-invalid") from None
    if len(payload) > MAX_JSON_BYTES:
        raise MessagesTransformError("messages-json-size-invalid")
    return payload


def _transform_request(document: dict[str, Any], transform: TextTransform) -> None:
    if "system" in document:
        document["system"] = _transform_content(
            document["system"], ContentKind.CONVERSATION, transform
        )
    messages = document.get("messages")
    if not isinstance(messages, list) or not messages:
        raise MessagesTransformError("messages-input-invalid")
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            raise MessagesTransformError("messages-input-invalid")
        if "content" not in message:
            raise MessagesTransformError("messages-input-invalid")
        message["content"] = _transform_content(
            message["content"], ContentKind.CONVERSATION, transform
        )
    if "tools" in document:
        tools = document["tools"]
        if not isinstance(tools, list):
            raise MessagesTransformError("messages-tools-invalid")
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                raise MessagesTransformError("messages-tools-invalid")
            tools[index] = _transform_json_tree(tool, ContentKind.TOOL_DEFINITION, transform)


def _transform_response(document: dict[str, Any], transform: TextTransform) -> None:
    if "content" in document:
        content = document["content"]
        if not isinstance(content, list):
            raise MessagesTransformError("messages-output-invalid")
        for block in content:
            if not isinstance(block, dict):
                raise MessagesTransformError("messages-output-invalid")
            _transform_output_block(block, transform)
    if "error" in document:
        error = document["error"]
        if error is not None:
            if not isinstance(error, dict):
                raise MessagesTransformError("messages-error-invalid")
            _transform_optional_string(error, "message", ContentKind.CONVERSATION, transform)


def _transform_content(
    value: object,
    default_kind: ContentKind,
    transform: TextTransform,
) -> object:
    if isinstance(value, str):
        return _call_transform(value, default_kind, transform)
    if not isinstance(value, list):
        raise MessagesTransformError("messages-content-invalid")
    for block in value:
        if not isinstance(block, dict):
            raise MessagesTransformError("messages-content-invalid")
        _transform_input_block(block, transform)
    return value


def _transform_input_block(block: dict[str, Any], transform: TextTransform) -> None:
    block_type = block.get("type")
    if not isinstance(block_type, str):
        raise MessagesTransformError("messages-content-invalid")
    if block_type == "text":
        _transform_required_string(block, "text", ContentKind.CONVERSATION, transform)
    elif block_type == "tool_use":
        _transform_required_string(block, "name", ContentKind.TOOL_HISTORY, transform)
        if "input" not in block or not isinstance(block["input"], dict):
            raise MessagesTransformError("messages-tool-input-invalid")
        block["input"] = _transform_json_tree(
            block["input"], ContentKind.TOOL_HISTORY, transform
        )
    elif block_type == "tool_result":
        if "content" in block:
            block["content"] = _transform_tool_result(block["content"], transform)
    elif block_type == "document":
        _transform_document(block, transform)
    elif block_type == "search_result":
        _transform_optional_string(block, "title", ContentKind.CONVERSATION, transform)
        content = block.get("content")
        if content is not None:
            block["content"] = _transform_content(
                content, ContentKind.CONVERSATION, transform
            )


def _transform_output_block(
    block: dict[str, Any],
    transform: TextTransform,
    *,
    allow_incomplete: bool = False,
) -> None:
    block_type = block.get("type")
    if not isinstance(block_type, str):
        raise MessagesTransformError("messages-output-invalid")
    if block_type == "text":
        if not allow_incomplete or "text" in block:
            _transform_required_string(block, "text", ContentKind.CONVERSATION, transform)
    elif block_type == "tool_use":
        if not allow_incomplete or "name" in block:
            _transform_required_string(block, "name", ContentKind.TOOL_DEFINITION, transform)
        if "input" in block:
            if not isinstance(block["input"], dict):
                raise MessagesTransformError("messages-tool-input-invalid")
            block["input"] = _transform_json_tree(
                block["input"], ContentKind.TOOL_ARGUMENT, transform
            )


def _transform_tool_result(value: object, transform: TextTransform) -> object:
    if isinstance(value, str):
        return _call_transform(value, ContentKind.TOOL_RESULT, transform)
    if not isinstance(value, list):
        raise MessagesTransformError("messages-tool-result-invalid")
    for block in value:
        if not isinstance(block, dict):
            raise MessagesTransformError("messages-tool-result-invalid")
        if block.get("type") == "text":
            _transform_required_string(block, "text", ContentKind.TOOL_RESULT, transform)
    return value


def _transform_document(block: dict[str, Any], transform: TextTransform) -> None:
    _transform_optional_string(block, "title", ContentKind.CONVERSATION, transform)
    _transform_optional_string(block, "context", ContentKind.CONVERSATION, transform)
    source = block.get("source")
    if not isinstance(source, dict):
        return
    if source.get("type") == "text":
        _transform_required_string(source, "data", ContentKind.CONVERSATION, transform)
    elif source.get("type") == "content" and "content" in source:
        source["content"] = _transform_content(
            source["content"], ContentKind.CONVERSATION, transform
        )


def _transform_json_tree(
    value: object,
    kind: ContentKind,
    transform: TextTransform,
) -> object:
    if isinstance(value, str):
        return _call_transform(value, kind, transform)
    if isinstance(value, list):
        return [_transform_json_tree(child, kind, transform) for child in value]
    if isinstance(value, dict):
        transformed: dict[str, Any] = {}
        for key, child in value.items():
            new_key = _call_transform(key, kind, transform)
            if new_key in transformed:
                raise MessagesTransformError("messages-transformed-key-collision")
            transformed[new_key] = _transform_json_tree(child, kind, transform)
        return transformed
    return value


def _transform_required_string(
    document: dict[str, Any],
    key: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    value = document.get(key)
    if not isinstance(value, str):
        raise MessagesTransformError("messages-content-invalid")
    document[key] = _call_transform(value, kind, transform)


def _transform_optional_string(
    document: dict[str, Any],
    key: str,
    kind: ContentKind,
    transform: TextTransform,
) -> None:
    if key not in document or document[key] is None:
        return
    _transform_required_string(document, key, kind, transform)


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
