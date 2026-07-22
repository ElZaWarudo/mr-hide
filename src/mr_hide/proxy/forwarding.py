"""Raw request and response forwarding without payload interpretation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

import httpx
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse

from mr_hide.proxy.headers import filter_request_headers, filter_response_headers


class ProxyTargetError(ValueError):
    """Raised when an ASGI request target is not origin-form."""


def build_upstream_url(base: httpx.URL, raw_path: bytes, query: bytes) -> httpx.URL:
    """Append an origin-form path while preserving base and request query bytes."""

    if not raw_path.startswith(b"/") or raw_path.startswith(b"//") or b"://" in raw_path:
        raise ProxyTargetError("Only origin-form request targets are accepted.")

    base_path, separator, base_query = base.raw_path.partition(b"?")
    if base_path == b"/":
        base_path = b""
    joined_path = base_path.rstrip(b"/") + raw_path
    query_parts = tuple(part for part in (base_query if separator else b"", query) if part)
    raw_target = joined_path
    if query_parts:
        raw_target += b"?" + b"&".join(query_parts)
    return base.copy_with(raw_path=raw_target)


async def stream_raw_response(response: httpx.Response) -> AsyncIterator[bytes]:
    """Yield undecoded upstream chunks and close the response on every exit path."""

    try:
        async for chunk in response.aiter_raw():
            yield chunk
    finally:
        await response.aclose()


async def forward_request(request: Request) -> Response:
    """Forward one declared inference request to the configured upstream."""

    client = cast(httpx.AsyncClient, request.app.state.http_client)
    upstream = cast(httpx.URL, request.app.state.upstream_url)
    raw_path = cast(bytes, request.scope.get("raw_path", b""))
    query = cast(bytes, request.scope.get("query_string", b""))
    try:
        target = build_upstream_url(upstream, raw_path, query)
    except ProxyTargetError:
        return PlainTextResponse("Invalid request target.", status_code=400)

    upstream_request = client.build_request(
        request.method,
        target,
        headers=filter_request_headers(request.headers.raw),
        content=request.stream(),
    )
    try:
        upstream_response = await client.send(
            upstream_request,
            stream=True,
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        return PlainTextResponse("Upstream request timed out.", status_code=504)
    except httpx.RequestError:
        return PlainTextResponse("Upstream is unavailable.", status_code=502)

    response = StreamingResponse(
        stream_raw_response(upstream_response),
        status_code=upstream_response.status_code,
        background=BackgroundTask(upstream_response.aclose),
    )
    response.raw_headers = list(filter_response_headers(upstream_response.headers.raw))
    return response
