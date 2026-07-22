from __future__ import annotations

import json

import pytest

import mr_hide.protocols.responses.json_body as json_module
from mr_hide.policy import (
    ContentKind,
    Direction,
    PolicyAction,
    ToolPolicy,
    decide_policy,
)
from mr_hide.privacy.mapping import MappingTable, restore_text, transform_text
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.responses import (
    ResponsesTransformError,
    transform_request_json,
    transform_response_json,
)


class RecordingTransform:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ContentKind]] = []

    def __call__(self, text: str, kind: ContentKind) -> str:
        self.calls.append((text, kind))
        return f"[{kind.value}:{text}]"


class PolicyFixture:
    def __init__(self, policy: ToolPolicy) -> None:
        self.policy = policy
        self.mappings = MappingTable()

    def outgoing(self, text: str, kind: ContentKind) -> str:
        decision = decide_policy(self.policy, Direction.TO_PROVIDER, kind)
        if decision.action is PolicyAction.PASS_THROUGH:
            return text
        detections = tuple(
            DetectedSpan(index, index + 5, "PERSON", 1.0, "en", "fixture")
            for index in range(len(text))
            if text.startswith("Alice", index)
        )
        result = transform_text(
            text,
            detections,
            self.mappings,
            mode=decision.substitution_mode,
        )
        self.mappings = result.mappings
        return result.text

    def incoming(self, text: str, _kind: ContentKind) -> str:
        return restore_text(text, self.mappings)


def decoded(payload: bytes) -> dict[str, object]:
    value = json.loads(payload)
    assert isinstance(value, dict)
    return value


def test_request_transforms_only_declared_conversation_fields() -> None:
    transform = RecordingTransform()
    request = {
        "model": "model-PRIVATE",
        "instructions": "developer PRIVATE",
        "input": [
            {"role": "user", "content": "hello PRIVATE", "unknown": "opaque PRIVATE"},
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "input_text", "text": "part PRIVATE", "extra": "opaque"},
                    {"type": "input_image", "image_url": "https://PRIVATE.invalid"},
                ],
            },
            {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "summary PRIVATE"}],
                "encrypted_content": "opaque PRIVATE",
            },
        ],
        "metadata": {"note": "opaque PRIVATE"},
    }

    result = decoded(transform_request_json(json.dumps(request).encode(), transform))

    assert result["model"] == "model-PRIVATE"
    assert result["metadata"] == {"note": "opaque PRIVATE"}
    items = result["input"]
    assert isinstance(items, list)
    assert items[0]["content"] == "[conversation:hello PRIVATE]"
    assert items[0]["unknown"] == "opaque PRIVATE"
    assert items[1]["content"][0]["text"] == "[conversation:part PRIVATE]"
    assert items[1]["content"][1]["image_url"] == "https://PRIVATE.invalid"
    assert items[2]["summary"][0]["text"] == "[conversation:summary PRIVATE]"
    assert items[2]["encrypted_content"] == "opaque PRIVATE"


def test_string_input_and_prompt_variable_values_are_conversation_text() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "input": "hello",
            "prompt": {
                "id": "prompt_PRIVATE",
                "variables": {"customer_name": "Alice", "count": 3},
            },
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))

    assert result["input"] == "[conversation:hello]"
    assert result["prompt"] == {
        "id": "prompt_PRIVATE",
        "variables": {"customer_name": "[conversation:Alice]", "count": 3},
    }


def test_declared_tool_definitions_transform_keys_and_string_values() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "tools": [
                {
                    "type": "function",
                    "name": "lookup_PRIVATE",
                    "description": "find PRIVATE",
                    "parameters": {
                        "type": "object",
                        "properties": {"PRIVATE_key": {"type": "string"}},
                    },
                }
            ],
            "other": {"PRIVATE_key": "opaque PRIVATE"},
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))
    tools = result["tools"]
    assert isinstance(tools, list)
    function = tools[0]

    assert "[tool-definition:PRIVATE_key]" in function["[tool-definition:parameters]"][
        "[tool-definition:properties]"
    ]
    assert result["other"] == {"PRIVATE_key": "opaque PRIVATE"}


def test_function_arguments_use_strict_inner_json_and_preserve_types() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "input": [
                {
                    "type": "function_call",
                    "name": "run",
                    "arguments": json.dumps(
                        {"path_PRIVATE": 'C:\\Users\\"PRIVATE"', "enabled": True}
                    ),
                }
            ]
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))
    items = result["input"]
    assert isinstance(items, list)
    arguments = json.loads(items[0]["arguments"])

    assert arguments == {
        "[tool-argument:path_PRIVATE]": '[tool-argument:C:\\Users\\"PRIVATE"]',
        "[tool-argument:enabled]": True,
    }
    assert items[0]["name"] == "[tool-definition:run]"


def test_function_output_and_custom_tool_input_use_tool_kinds() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "input": [
                {"type": "function_call_output", "call_id": "1", "output": "PRIVATE"},
                {"type": "custom_tool_call", "name": "shell", "input": "echo PRIVATE"},
            ]
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))
    items = result["input"]
    assert isinstance(items, list)

    assert items[0]["output"] == "[tool-result:PRIVATE]"
    assert items[1]["input"] == "[tool-argument:echo PRIVATE]"
    assert items[1]["name"] == "[tool-definition:shell]"


def test_response_restores_output_tool_arguments_and_error_message() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "id": "resp_PRIVATE",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "answer PRIVATE", "annotations": []}
                    ],
                },
                {
                    "type": "function_call",
                    "name": "run",
                    "arguments": '{"value":"PRIVATE"}',
                },
            ],
            "error": {"code": "bad_PRIVATE", "message": "failed PRIVATE"},
            "usage": {"input_tokens": 10},
        }
    ).encode()

    result = decoded(transform_response_json(payload, transform))
    output = result["output"]
    assert isinstance(output, list)

    assert output[0]["content"][0]["text"] == "[conversation:answer PRIVATE]"
    assert json.loads(output[1]["arguments"]) == {
        "[tool-argument:value]": "[tool-argument:PRIVATE]"
    }
    assert result["error"] == {
        "code": "bad_PRIVATE",
        "message": "[conversation:failed PRIVATE]",
    }
    assert result["usage"] == {"input_tokens": 10}
    assert result["id"] == "resp_PRIVATE"


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (b"", "responses-json-size-invalid"),
        (b"[]", "responses-json-invalid"),
        (b'{"input":"x","input":"y"}', "responses-json-duplicate-key"),
        (b'{"temperature":NaN}', "responses-json-invalid"),
        (b'\xff', "responses-json-invalid"),
    ),
)
def test_invalid_outer_json_fails_closed(payload: bytes, reason: str) -> None:
    with pytest.raises(ResponsesTransformError, match=reason):
        transform_request_json(payload, RecordingTransform())


@pytest.mark.parametrize(
    "arguments",
    ('{"x":1,"x":2}', "not-json", "[]"),
)
def test_invalid_inner_tool_json_fails_closed(arguments: str) -> None:
    payload = json.dumps(
        {"input": [{"type": "function_call", "arguments": arguments}]}
    ).encode()

    with pytest.raises(ResponsesTransformError):
        transform_request_json(payload, RecordingTransform())


def test_transformed_tool_key_collision_is_rejected() -> None:
    payload = json.dumps({"tools": [{"a": "one", "b": "two"}]}).encode()

    with pytest.raises(ResponsesTransformError, match="responses-transformed-key-collision"):
        transform_request_json(payload, lambda _text, _kind: "same")


def test_transform_exception_is_redacted() -> None:
    def fail(_text: str, _kind: ContentKind) -> str:
        raise RuntimeError("PRIVATE_SENTINEL")

    with pytest.raises(ResponsesTransformError, match="responses-text-transform-failed") as caught:
        transform_request_json(b'{"input":"PRIVATE"}', fail)

    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    ("policy", "conversation_value", "tool_value"),
    (
        (ToolPolicy.DEFAULT, "<P0>", "Alice"),
        (ToolPolicy.SAFE_TOOL_CALLS, "<P0>", "<P0>"),
        (ToolPolicy.TOOL_COMPATIBILITY, "Alex Morgan", "Alex Morgan"),
    ),
)
def test_all_policies_apply_to_conversation_and_tool_fields(
    policy: ToolPolicy,
    conversation_value: str,
    tool_value: str,
) -> None:
    fixture = PolicyFixture(policy)
    request = json.dumps(
        {
            "input": "Alice",
            "tools": [{"type": "function", "description": "Alice"}],
            "metadata": {"opaque": "Alice"},
        }
    ).encode()

    transformed = decoded(transform_request_json(request, fixture.outgoing))
    tools = transformed["tools"]
    assert isinstance(tools, list)
    assert transformed["input"] == conversation_value
    assert tools[0]["description"] == tool_value
    assert transformed["metadata"] == {"opaque": "Alice"}

    response = json.dumps(
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": conversation_value}],
                },
                {
                    "type": "function_call",
                    "name": "lookup",
                    "arguments": json.dumps({"person": tool_value}),
                },
            ]
        }
    ).encode()
    restored = decoded(transform_response_json(response, fixture.incoming))
    output = restored["output"]
    assert isinstance(output, list)
    assert output[0]["content"][0]["text"] == "Alice"
    assert json.loads(output[1]["arguments"])["person"] == "Alice"


def test_post_transform_expansion_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b'{"input":"x"}'
    monkeypatch.setattr(json_module, "MAX_JSON_BYTES", 32)

    with pytest.raises(ResponsesTransformError, match="responses-json-size-invalid"):
        transform_request_json(payload, lambda _text, _kind: "x" * 100)


def test_excessive_json_depth_is_rejected() -> None:
    value: object = "leaf"
    for _ in range(66):
        value = [value]
    payload = json.dumps({"input": value}).encode()

    with pytest.raises(ResponsesTransformError, match="responses-json-too-deep"):
        transform_request_json(payload, RecordingTransform())


def test_non_object_tool_definition_is_rejected() -> None:
    with pytest.raises(ResponsesTransformError, match="responses-tools-invalid"):
        transform_request_json(b'{"tools":["function"]}', RecordingTransform())
