from __future__ import annotations

import httpx
import pytest

from mr_hide.proxy.forwarding import stream_raw_response
from tests.fixtures.upstream_app import TrackedByteStream


@pytest.mark.asyncio
async def test_raw_response_preserves_chunk_order_and_split_utf8() -> None:
    chunks = (
        b": comment\n\n",
        b"data: \xe2\x82",
        b"\xac\n\n",
        b"data:\n\n",
        b"data: [DONE]\n\n",
    )
    stream = TrackedByteStream(chunks)
    response = httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        stream=stream,
        request=httpx.Request("POST", "https://upstream.test/v1/responses"),
    )

    received = tuple([chunk async for chunk in stream_raw_response(response)])

    assert received == chunks
    assert stream.closed


@pytest.mark.asyncio
async def test_downstream_cancellation_closes_upstream_response() -> None:
    stream = TrackedByteStream((b"first", b"second"))
    response = httpx.Response(
        200,
        stream=stream,
        request=httpx.Request("POST", "https://upstream.test/v1/responses"),
    )
    iterator = stream_raw_response(response)

    assert await anext(iterator) == b"first"
    await iterator.aclose()

    assert stream.closed


@pytest.mark.asyncio
async def test_midstream_failure_closes_upstream_response() -> None:
    stream = TrackedByteStream((b"first",), failure=httpx.ReadError("stream failed"))
    response = httpx.Response(
        200,
        stream=stream,
        request=httpx.Request("POST", "https://upstream.test/v1/responses"),
    )

    with pytest.raises(httpx.ReadError, match="stream failed"):
        tuple([chunk async for chunk in stream_raw_response(response)])

    assert stream.closed

