from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from mr_hide.policy import ContentKind
from mr_hide.protocols.messages import (
    MessagesTransformError,
    transform_sse_bytes,
    transform_sse_stream,
)


def transform(text: str, kind: ContentKind) -> str:
    return f"[{kind.value}:{text}]"


def frame(event: dict[str, object], *, newline: str = "\n") -> bytes:
    return (
        f"event: {event['type']}{newline}"
        f"data: {json.dumps(event, separators=(',', ':'))}{newline}{newline}"
    ).encode()


def decoded_events(payload: bytes) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for raw in payload.replace(b"\r\n", b"\n").split(b"\n\n"):
        if not raw:
            continue
        data = next(line[6:] for line in raw.splitlines() if line.startswith(b"data: "))
        events.append(json.loads(data))
    return events


def test_text_delta_is_withheld_until_content_block_stop() -> None:
    payload = b"".join(
        (
            frame(
                {"type": "message_start", "message": {"content": [], "usage": {"input_tokens": 1}}}
            ),
            frame(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "Ali"},
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "ce"},
                }
            ),
            frame({"type": "ping"}),
            frame({"type": "content_block_stop", "index": 0}),
            frame(
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 1},
                }
            ),
            frame({"type": "message_stop"}),
        )
    )

    result = transform_sse_bytes(payload, transform)
    events = decoded_events(result)

    deltas = [event for event in events if event["type"] == "content_block_delta"]
    assert deltas[0]["delta"]["text"] == "[conversation:Alice]"
    assert deltas[1]["delta"]["text"] == ""
    assert events[4] == {"type": "ping"}
    assert events[-2]["usage"] == {"output_tokens": 1}


def test_partial_tool_json_is_reconstructed_strictly() -> None:
    payload = b"".join(
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": 2,
                    "content_block": {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "lookup",
                        "input": {},
                    },
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 2,
                    "delta": {"type": "input_json_delta", "partial_json": '{"owner":"Ali'},
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 2,
                    "delta": {"type": "input_json_delta", "partial_json": 'ce","count":2}'},
                }
            ),
            frame({"type": "content_block_stop", "index": 2}),
        )
    )

    events = decoded_events(transform_sse_bytes(payload, transform))
    partials = [
        event["delta"]["partial_json"] for event in events if event["type"] == "content_block_delta"
    ]

    assert json.loads("".join(partials)) == {
        "[tool-argument:owner]": "[tool-argument:Alice]",
        "[tool-argument:count]": 2,
    }


def test_unknown_event_is_preserved_byte_exact_with_crlf_and_comments() -> None:
    unknown = (
        b': keep\r\nevent: future.event\r\ndata: {"type":"future.event","text":"PRIVATE"}\r\n\r\n'
    )
    known = frame(
        {"type": "error", "error": {"type": "api_error", "message": "PRIVATE"}}, newline="\r\n"
    )

    result = transform_sse_bytes(unknown + known, transform)

    assert result.startswith(unknown)
    assert b"[conversation:PRIVATE]" in result


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (frame({"type": "content_block_stop", "index": 0}), "messages-sse-block-order-invalid"),
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": -1,
                    "content_block": {"type": "text", "text": ""},
                }
            ),
            "messages-sse-index-invalid",
        ),
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
            ),
            "messages-sse-incomplete-block",
        ),
        (
            b'event: ping\ndata: {"type":"message_stop"}\n\n',
            "messages-sse-event-mismatch",
        ),
    ),
)
def test_invalid_streams_fail_closed(payload: bytes, reason: str) -> None:
    with pytest.raises(MessagesTransformError, match=reason):
        transform_sse_bytes(payload, transform)


def test_duplicate_partial_tool_json_is_rejected() -> None:
    payload = b"".join(
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "tool_use", "id": "x", "name": "x", "input": {}},
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "input_json_delta", "partial_json": '{"x":1,"x":2}'},
                }
            ),
            frame({"type": "content_block_stop", "index": 0}),
        )
    )

    with pytest.raises(MessagesTransformError, match="messages-json-duplicate-key"):
        transform_sse_bytes(payload, transform)


def test_deep_partial_tool_json_is_rejected() -> None:
    value: object = "x"
    for _ in range(66):
        value = {"x": value}
    payload = b"".join(
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": "x",
                        "name": "x",
                        "input": {},
                    },
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps(value),
                    },
                }
            ),
            frame({"type": "content_block_stop", "index": 0}),
        )
    )

    with pytest.raises(MessagesTransformError, match="messages-json-too-deep"):
        transform_sse_bytes(payload, transform)


@pytest.mark.asyncio
async def test_async_chunks_emit_nothing_before_complete_success() -> None:
    payload = b"".join(
        (
            frame(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
            ),
            frame(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "Alice"},
                }
            ),
            frame({"type": "content_block_stop", "index": 0}),
        )
    )

    async def chunks() -> AsyncIterator[bytes]:
        for index in range(0, len(payload), 3):
            yield payload[index : index + 3]

    output = [chunk async for chunk in transform_sse_stream(chunks(), transform)]
    assert len(output) == 1
    assert b"[conversation:Alice]" in output[0]

    emitted: list[bytes] = []

    async def incomplete() -> AsyncIterator[bytes]:
        yield frame(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }
        )

    with pytest.raises(MessagesTransformError):
        async for chunk in transform_sse_stream(incomplete(), transform):
            emitted.append(chunk)
    assert emitted == []
