from __future__ import annotations

import json
from collections.abc import AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

CONTRACT_REPLY = "CONTRACT_OK"


def _sse(
    events: list[dict[str, object]],
    *,
    named_events: bool = False,
) -> StreamingResponse:
    async def stream() -> AsyncIterator[bytes]:
        for event in events:
            prefix = f"event: {event['type']}\n" if named_events else ""
            yield (
                f"{prefix}data: {json.dumps(event, separators=(',', ':'))}\n\n"
            ).encode()

    return StreamingResponse(stream(), media_type="text/event-stream")


async def responses(request: Request) -> StreamingResponse:
    request.app.state.captured_bodies.append(await request.body())
    response = {
        "id": "resp_contract",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "completed_at": 1,
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "model": "gpt-5.1-codex-mini",
        "output": [
            {
                "id": "msg_contract",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": CONTRACT_REPLY, "annotations": []}
                ],
            }
        ],
        "parallel_tool_calls": True,
        "temperature": 1,
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1,
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 2,
        },
    }
    message = response["output"][0]
    part = message["content"][0]
    events = [
        {
            "type": "response.created",
            "response": {**response, "status": "in_progress", "output": []},
        },
        {
            "type": "response.output_item.added",
            "output_index": 0,
            "item": {**message, "status": "in_progress", "content": []},
        },
        {
            "type": "response.content_part.added",
            "item_id": "msg_contract",
            "output_index": 0,
            "content_index": 0,
            "part": {**part, "text": ""},
        },
        {
            "type": "response.output_text.delta",
            "item_id": "msg_contract",
            "output_index": 0,
            "content_index": 0,
            "delta": CONTRACT_REPLY,
        },
        {
            "type": "response.output_text.done",
            "item_id": "msg_contract",
            "output_index": 0,
            "content_index": 0,
            "text": CONTRACT_REPLY,
        },
        {
            "type": "response.content_part.done",
            "item_id": "msg_contract",
            "output_index": 0,
            "content_index": 0,
            "part": part,
        },
        {
            "type": "response.output_item.done",
            "output_index": 0,
            "item": message,
        },
        {"type": "response.completed", "response": response},
    ]
    return _sse(events)


async def count_tokens(request: Request) -> JSONResponse:
    request.app.state.captured_bodies.append(await request.body())
    return JSONResponse({"input_tokens": 1})


async def messages(request: Request) -> StreamingResponse:
    request.app.state.captured_bodies.append(await request.body())
    message = {
        "id": "msg_contract",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-4-5-20250929",
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 0},
    }
    events = [
        {"type": "message_start", "message": message},
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": CONTRACT_REPLY},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": 1},
        },
        {"type": "message_stop"},
    ]
    return _sse(events, named_events=True)


def create_contract_app(captured_bodies: list[bytes] | None = None) -> Starlette:
    app = Starlette(
        routes=[
            Route("/v1/responses", responses, methods=["POST"]),
            Route("/v1/messages", messages, methods=["POST"]),
            Route("/v1/messages/count_tokens", count_tokens, methods=["POST"]),
        ]
    )
    app.state.captured_bodies = [] if captured_bodies is None else captured_bodies
    return app
