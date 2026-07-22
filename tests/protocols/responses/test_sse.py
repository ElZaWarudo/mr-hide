from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from mr_hide.policy import ContentKind
from mr_hide.protocols.responses import (
    ResponsesTransformError,
    transform_sse_bytes,
    transform_sse_stream,
)


def event(document: dict[str, object], *, newline: str = "\n") -> bytes:
    payload = json.dumps(document, separators=(",", ":"))
    return f"data: {payload}{newline}{newline}".encode()


def documents(payload: bytes) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    normalized = payload.replace(b"\r\n", b"\n")
    for frame in normalized.split(b"\n\n"):
        data = [line[5:].lstrip() for line in frame.splitlines() if line.startswith(b"data:")]
        if data and data != [b"[DONE]"]:
            value = json.loads(b"\n".join(data))
            assert isinstance(value, dict)
            result.append(value)
    return result


def restore_alias(text: str, _kind: ContentKind) -> str:
    return text.replace("<P0>", "Alice")


def test_split_output_alias_is_restored_atomically_without_reordering() -> None:
    payload = b"".join(
        (
            event(
                {
                    "type": "response.output_text.delta",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "delta": "Hello <P",
                    "sequence_number": 1,
                }
            ),
            event(
                {
                    "type": "response.output_text.delta",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "delta": "0>",
                    "sequence_number": 2,
                }
            ),
            event(
                {
                    "type": "response.output_text.done",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "text": "Hello <P0>",
                    "sequence_number": 3,
                }
            ),
            event(
                {
                    "type": "response.completed",
                    "response": {
                        "id": "r1",
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {"type": "output_text", "text": "Hello <P0>"}
                                ],
                            }
                        ],
                    },
                    "sequence_number": 4,
                }
            ),
        )
    )

    result = documents(transform_sse_bytes(payload, restore_alias))

    assert [item["sequence_number"] for item in result] == [1, 2, 3, 4]
    assert result[0]["delta"] == "Hello Alice"
    assert result[1]["delta"] == ""
    assert result[2]["text"] == "Hello Alice"
    assert result[3]["response"]["output"][0]["content"][0]["text"] == "Hello Alice"


def test_split_function_arguments_are_parsed_as_inner_json() -> None:
    payload = b"".join(
        (
            event(
                {
                    "type": "response.function_call_arguments.delta",
                    "item_id": "f1",
                    "output_index": 0,
                    "delta": '{"name":"<P',
                }
            ),
            event(
                {
                    "type": "response.function_call_arguments.delta",
                    "item_id": "f1",
                    "output_index": 0,
                    "delta": '0>"}',
                }
            ),
            event(
                {
                    "type": "response.function_call_arguments.done",
                    "item_id": "f1",
                    "output_index": 0,
                    "name": "lookup",
                    "arguments": '{"name":"<P0>"}',
                }
            ),
        )
    )

    result = documents(transform_sse_bytes(payload, restore_alias))

    assert json.loads(result[0]["delta"]) == {"name": "Alice"}
    assert result[1]["delta"] == ""
    assert json.loads(result[2]["arguments"]) == {"name": "Alice"}


def test_unknown_events_and_done_marker_are_byte_exact() -> None:
    unknown = (
        b":keep\r\nevent: future\r\ndata: {"
        + b'"type":"response.future","text":"<P0>"}'
        + b"\r\n\r\n"
    )
    done = b"data: [DONE]\n\n"

    assert transform_sse_bytes(unknown + done, restore_alias) == unknown + done


def test_known_event_preserves_non_data_fields_and_crlf() -> None:
    payload = (
        b"id: 7\r\n"
        b"event: error\r\n"
        b'data: {"type":"error","message":"bad <P0>"}\r\n\r\n'
    )

    result = transform_sse_bytes(payload, restore_alias)

    assert result.startswith(b"id: 7\r\nevent: error\r\n")
    assert b"bad Alice" in result
    assert result.endswith(b"\r\n\r\n")


def test_complete_item_and_content_part_events_are_restored() -> None:
    payload = event(
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "name": "lookup",
                "arguments": '{"person":"<P0>"}',
            },
        }
    ) + event(
        {
            "type": "response.content_part.done",
            "part": {"type": "output_text", "text": "Hello <P0>"},
        }
    )

    result = documents(transform_sse_bytes(payload, restore_alias))

    assert json.loads(result[0]["item"]["arguments"]) == {"person": "Alice"}
    assert result[1]["part"]["text"] == "Hello Alice"


def test_incomplete_added_item_preserves_empty_arguments_and_restores_name() -> None:
    payload = event(
        {
            "type": "response.output_item.added",
            "item": {
                "type": "function_call",
                "name": "lookup_<P0>",
                "arguments": "",
            },
        }
    )

    result = documents(transform_sse_bytes(payload, restore_alias))[0]

    assert result["item"]["name"] == "lookup_Alice"
    assert result["item"]["arguments"] == ""


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (
            event(
                {
                    "type": "response.output_text.delta",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "delta": "partial",
                }
            ),
            "responses-sse-incomplete-delta",
        ),
        (
            event(
                {
                    "type": "response.output_text.delta",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "delta": "one",
                }
            )
            + event(
                {
                    "type": "response.output_text.done",
                    "item_id": "m1",
                    "output_index": 0,
                    "content_index": 0,
                    "text": "different",
                }
            ),
            "responses-sse-delta-mismatch",
        ),
        (b'data: {"type":"error","message":"x","message":"y"}\n\n', "duplicate"),
        (b"data: \xff\n\n", "responses-sse-invalid"),
        (b"data: {\"type\":1}\n\n", "responses-sse-event-invalid"),
        (event({"type": "response.created", "response": None}), "event-invalid"),
    ),
)
def test_malformed_or_incomplete_streams_fail_closed(payload: bytes, reason: str) -> None:
    with pytest.raises(ResponsesTransformError, match=reason):
        transform_sse_bytes(payload, restore_alias)


@pytest.mark.asyncio
async def test_async_stream_accepts_arbitrary_chunk_boundaries() -> None:
    payload = event(
        {
            "type": "error",
            "code": "bad",
            "message": "failed <P0>",
            "sequence_number": 1,
        }
    )

    async def chunks() -> AsyncIterator[bytes]:
        for index in range(0, len(payload), 3):
            yield payload[index : index + 3]

    result = b"".join([chunk async for chunk in transform_sse_stream(chunks(), restore_alias)])

    assert documents(result)[0]["message"] == "failed Alice"


@pytest.mark.asyncio
async def test_async_stream_emits_nothing_before_failure() -> None:
    yielded: list[bytes] = []

    async def chunks() -> AsyncIterator[bytes]:
        yield event(
            {
                "type": "response.output_text.delta",
                "item_id": "m1",
                "output_index": 0,
                "content_index": 0,
                "delta": "PRIVATE",
            }
        )

    with pytest.raises(ResponsesTransformError, match="responses-sse-incomplete-delta"):
        async for chunk in transform_sse_stream(chunks(), restore_alias):
            yielded.append(chunk)

    assert yielded == []
