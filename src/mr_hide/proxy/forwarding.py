"""Raw request and response forwarding without payload interpretation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

import httpx
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse

from mr_hide.policy import Direction
from mr_hide.protocols.responses import (
    ResponsesRuntime,
    ResponsesRuntimeError,
    ResponsesTransformError,
    transform_request_json,
    transform_response_json,
    transform_sse_bytes,
)
from mr_hide.proxy.headers import filter_request_headers, filter_response_headers

_MAX_TRANSFORMED_RESPONSE_BYTES = 32 * 1024 * 1024


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

    runtime = cast(ResponsesRuntime | None, request.app.state.responses_runtime)
    if request.url.path == "/v1/responses" and runtime is not None:
        return await _forward_protected_responses(request, runtime)

    client = cast(httpx.AsyncClient, request.app.state.http_client)
    upstream = cast(httpx.URL, request.app.state.upstream_url)
    raw_path = cast(bytes, request.scope.get("raw_path", b""))
    query = cast(bytes, request.scope.get("query_string", b""))
    try:
        target = build_upstream_url(upstream, raw_path, query)
    except ProxyTargetError:
        return PlainTextResponse("Invalid request target.", status_code=400)

    # Construct the request directly so the lifespan-scoped client cannot merge
    # defaults or replay cookies learned from an earlier upstream response.
    upstream_request = httpx.Request(
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


async def _forward_protected_responses(
    request: Request,
    runtime: ResponsesRuntime,
) -> Response:
    client = cast(httpx.AsyncClient, request.app.state.http_client)
    upstream = cast(httpx.URL, request.app.state.upstream_url)
    raw_path = cast(bytes, request.scope.get("raw_path", b""))
    query = cast(bytes, request.scope.get("query_string", b""))
    try:
        target = build_upstream_url(upstream, raw_path, query)
        original = await _bounded_request_body(request)
        transaction = runtime.transaction(Direction.TO_PROVIDER)
        protected = transform_request_json(original, transaction.transform)
        runtime.bind_request_identity(original)
        transaction.commit()
    except ProxyTargetError:
        return PlainTextResponse("Invalid request target.", status_code=400)
    except (ResponsesTransformError, ResponsesRuntimeError) as error:
        return PlainTextResponse(f"Protected request rejected ({error.reason}).", status_code=400)

    request_headers = _rewritten_request_headers(request.headers.raw)
    upstream_request = httpx.Request(
        request.method,
        target,
        headers=request_headers,
        content=protected,
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

    try:
        payload = await _bounded_response_body(upstream_response)
        incoming = runtime.transaction(Direction.TO_LOCAL)
        media_type = upstream_response.headers.get("content-type", "").split(";", 1)[0]
        if media_type.strip().lower() == "text/event-stream":
            restored = transform_sse_bytes(payload, incoming.transform)
        else:
            restored = transform_response_json(payload, incoming.transform)
        incoming.commit()
    except (ResponsesTransformError, ResponsesRuntimeError, httpx.RequestError):
        return PlainTextResponse("Protected upstream response rejected.", status_code=502)
    finally:
        await upstream_response.aclose()

    response = Response(content=restored, status_code=upstream_response.status_code)
    response.raw_headers = list(_rewritten_response_headers(upstream_response.headers.raw))
    return response


async def _bounded_request_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > _MAX_TRANSFORMED_RESPONSE_BYTES:
            raise ResponsesRuntimeError("responses-json-size-invalid")
        chunks.append(chunk)
    return b"".join(chunks)


async def _bounded_response_body(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > _MAX_TRANSFORMED_RESPONSE_BYTES:
            raise ResponsesRuntimeError("responses-response-too-large")
        chunks.append(chunk)
    return b"".join(chunks)


def _rewritten_request_headers(
    headers: list[tuple[bytes, bytes]],
) -> tuple[tuple[bytes, bytes], ...]:
    filtered = filter_request_headers(headers)
    excluded = {b"content-length", b"content-encoding", b"accept-encoding"}
    return (
        *((name, value) for name, value in filtered if name.lower() not in excluded),
        (b"accept-encoding", b"identity"),
    )


def _rewritten_response_headers(
    headers: list[tuple[bytes, bytes]],
) -> tuple[tuple[bytes, bytes], ...]:
    filtered = filter_response_headers(headers)
    excluded = {b"content-length", b"content-encoding"}
    return tuple((name, value) for name, value in filtered if name.lower() not in excluded)
