from __future__ import annotations

import json

import pytest

import mr_hide.protocols.messages.json_body as json_module
from mr_hide.policy import (
    ContentKind,
    Direction,
    PolicyAction,
    ToolPolicy,
    decide_policy,
)
from mr_hide.privacy.mapping import MappingTable, restore_text, transform_text
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.messages import (
    MessagesTransformError,
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
    result = json.loads(payload)
    assert isinstance(result, dict)
    return result


def test_request_transforms_only_declared_conversation_fields() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "model": "model_PRIVATE",
            "system": [{"type": "text", "text": "system PRIVATE", "x": "opaque"}],
            "messages": [
                {"role": "user", "content": "hello PRIVATE", "x": "opaque PRIVATE"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "answer PRIVATE"},
                        {
                            "type": "image",
                            "source": {"type": "base64", "data": "PRIVATE"},
                        },
                        {"type": "thinking", "thinking": "PRIVATE", "signature": "PRIVATE"},
                    ],
                },
            ],
            "metadata": {"user_id": "PRIVATE"},
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))

    assert result["model"] == "model_PRIVATE"
    assert result["metadata"] == {"user_id": "PRIVATE"}
    assert result["system"][0]["text"] == "[conversation:system PRIVATE]"
    assert result["messages"][0]["content"] == "[conversation:hello PRIVATE]"
    blocks = result["messages"][1]["content"]
    assert blocks[0]["text"] == "[conversation:answer PRIVATE]"
    assert blocks[1]["source"]["data"] == "PRIVATE"
    assert blocks[2]["thinking"] == "PRIVATE"


@pytest.mark.parametrize("policy", tuple(ToolPolicy))
def test_tool_definitions_history_and_results_follow_policy(policy: ToolPolicy) -> None:
    fixture = PolicyFixture(policy)
    payload = json.dumps(
        {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "Alice",
                            "input": {"owner": "Alice"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "Alice result"}
                    ],
                },
            ],
            "tools": [
                {"name": "Alice", "description": "Find Alice", "input_schema": {"type": "object"}}
            ],
        }
    ).encode()

    result = transform_request_json(payload, fixture.outgoing)

    if policy is ToolPolicy.DEFAULT:
        assert b"Alice" in result
    else:
        assert b"Alice" not in result


def test_document_and_search_text_are_declared_but_binary_data_is_opaque() -> None:
    transform = RecordingTransform()
    payload = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "title": "PRIVATE title",
                            "source": {"type": "text", "data": "PRIVATE data"},
                        },
                        {
                            "type": "search_result",
                            "title": "PRIVATE result",
                            "source": "https://PRIVATE.invalid",
                            "content": [{"type": "text", "text": "PRIVATE excerpt"}],
                        },
                    ],
                }
            ]
        }
    ).encode()

    result = decoded(transform_request_json(payload, transform))
    blocks = result["messages"][0]["content"]

    assert blocks[0]["title"] == "[conversation:PRIVATE title]"
    assert blocks[0]["source"]["data"] == "[conversation:PRIVATE data]"
    assert blocks[1]["content"][0]["text"] == "[conversation:PRIVATE excerpt]"
    assert blocks[1]["source"] == "https://PRIVATE.invalid"


def test_response_restores_text_tool_input_and_error_only() -> None:
    fixture = PolicyFixture(ToolPolicy.SAFE_TOOL_CALLS)
    transform_request_json(
        json.dumps({"messages": [{"role": "user", "content": "Alice"}]}).encode(),
        fixture.outgoing,
    )
    payload = json.dumps(
        {
            "content": [
                {"type": "text", "text": "Hello <P0>"},
                {"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"owner": "<P0>"}},
                {"type": "thinking", "thinking": "<P0>", "signature": "<P0>"},
            ],
            "usage": {"input_tokens": 4},
            "unknown": "<P0>",
        }
    ).encode()

    result = decoded(transform_response_json(payload, fixture.incoming))

    assert result["content"][0]["text"] == "Hello Alice"
    assert result["content"][1]["input"] == {"owner": "Alice"}
    assert result["content"][2]["thinking"] == "<P0>"
    assert result["unknown"] == "<P0>"
    assert result["usage"] == {"input_tokens": 4}


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (b'{"messages":[],"messages":[]}', "messages-json-duplicate-key"),
        (b'{"messages":[{"role":"user","content":"x"}],"x":NaN}', "messages-json-invalid"),
        (b"[]", "messages-json-invalid"),
        (b'{"messages":[]}', "messages-input-invalid"),
        (b'{"messages":[{"role":"user","content":[{"text":"x"}]}]}', "messages-content-invalid"),
    ),
)
def test_invalid_requests_fail_with_stable_reasons(payload: bytes, reason: str) -> None:
    with pytest.raises(MessagesTransformError, match=reason):
        transform_request_json(payload, RecordingTransform())


def test_depth_and_post_transform_expansion_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    deep: object = "value"
    for _ in range(json_module.MAX_JSON_DEPTH + 2):
        deep = [deep]
    payload = json.dumps({"messages": [{"role": "user", "content": "x"}], "opaque": deep}).encode()
    with pytest.raises(MessagesTransformError, match="messages-json-too-deep"):
        transform_request_json(payload, RecordingTransform())

    monkeypatch.setattr(json_module, "MAX_JSON_BYTES", 128)
    with pytest.raises(MessagesTransformError, match="messages-json-size-invalid"):
        transform_request_json(
            b'{"messages":[{"role":"user","content":"x"}]}',
            lambda text, _kind: text * 200,
        )


def test_callback_exception_details_are_redacted() -> None:
    def fail(_text: str, _kind: ContentKind) -> str:
        raise RuntimeError("PRIVATE_CALLBACK_SENTINEL")

    with pytest.raises(MessagesTransformError) as caught:
        transform_request_json(
            b'{"messages":[{"role":"user","content":"x"}]}',
            fail,
        )

    assert str(caught.value) == "messages-text-transform-failed"
    assert "PRIVATE_CALLBACK_SENTINEL" not in str(caught.value)
