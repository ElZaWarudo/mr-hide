"""Raw request and response forwarding without payload interpretation."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import cast

import httpx
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse

from mr_hide.policy import ContentKind, Direction
from mr_hide.protocols.messages import (
    MessagesRuntime,
    MessagesRuntimeError,
    MessagesTransformError,
)
from mr_hide.protocols.messages import (
    transform_request_json as transform_messages_request,
)
from mr_hide.protocols.messages import (
    transform_response_json as transform_messages_response,
)
from mr_hide.protocols.messages import (
    transform_sse_bytes as transform_messages_sse,
)
from mr_hide.protocols.responses import (
    ResponsesRuntime,
    ResponsesRuntimeError,
    ResponsesTransformError,
    transform_request_json,
    transform_response_json,
    transform_sse_bytes,
)
from mr_hide.proxy.headers import filter_request_headers, filter_response_headers
from mr_hide.runtime.privacy import PrivacyRuntime, PrivacyRuntimeError

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
    messages_runtime = cast(MessagesRuntime | None, request.app.state.messages_runtime)
    if request.url.path in {"/v1/messages", "/v1/messages/count_tokens"} and messages_runtime:
        return await _forward_protected_messages(
            request,
            messages_runtime,
            count_only=request.url.path.endswith("/count_tokens"),
        )

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
        protected = await _transform_committed(
            runtime,
            Direction.TO_PROVIDER,
            original,
            transform_request_json,
            bind_identity=lambda: runtime.bind_request_identity(original),
        )
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
        media_type = upstream_response.headers.get("content-type", "").split(";", 1)[0]
        media_type = media_type.strip().lower()
        if upstream_response.status_code in {204, 205, 304}:
            return _safe_empty_response(upstream_response)
        if upstream_response.status_code >= 400 and not _is_structured_media_type(media_type):
            return _safe_unstructured_error(upstream_response)
        payload = await _bounded_response_body(upstream_response)
        if media_type == "text/event-stream":
            transformer = transform_sse_bytes
        else:
            transformer = transform_response_json
        restored = await _transform_committed(runtime, Direction.TO_LOCAL, payload, transformer)
    except (ResponsesTransformError, ResponsesRuntimeError, httpx.RequestError):
        return PlainTextResponse("Protected upstream response rejected.", status_code=502)
    finally:
        await upstream_response.aclose()

    response = Response(content=restored, status_code=upstream_response.status_code)
    response.raw_headers = list(_rewritten_response_headers(upstream_response.headers.raw))
    return response


async def _forward_protected_messages(
    request: Request,
    runtime: MessagesRuntime,
    *,
    count_only: bool,
) -> Response:
    client = cast(httpx.AsyncClient, request.app.state.http_client)
    upstream = cast(httpx.URL, request.app.state.upstream_url)
    raw_path = cast(bytes, request.scope.get("raw_path", b""))
    query = cast(bytes, request.scope.get("query_string", b""))
    try:
        target = build_upstream_url(upstream, raw_path, query)
        original = await _bounded_request_body(
            request, reason="messages-json-size-invalid"
        )
        protected = await _transform_committed(
            runtime, Direction.TO_PROVIDER, original, transform_messages_request
        )
    except ProxyTargetError:
        return PlainTextResponse("Invalid request target.", status_code=400)
    except (MessagesTransformError, MessagesRuntimeError) as error:
        return PlainTextResponse(f"Protected request rejected ({error.reason}).", status_code=400)

    upstream_request = httpx.Request(
        request.method,
        target,
        headers=_rewritten_request_headers(request.headers.raw),
        content=protected,
    )
    try:
        upstream_response = await client.send(upstream_request, stream=True, follow_redirects=False)
    except httpx.TimeoutException:
        return PlainTextResponse("Upstream request timed out.", status_code=504)
    except httpx.RequestError:
        return PlainTextResponse("Upstream is unavailable.", status_code=502)

    try:
        media_type = upstream_response.headers.get("content-type", "").split(";", 1)[0]
        media_type = media_type.strip().lower()
        if upstream_response.status_code in {204, 205, 304}:
            return _safe_empty_response(upstream_response)
        if upstream_response.status_code >= 400 and not _is_structured_media_type(media_type):
            return _safe_unstructured_error(upstream_response)
        payload = await _bounded_response_body(
            upstream_response, reason="messages-response-too-large"
        )
        if media_type == "text/event-stream":
            transformer = transform_messages_sse
        else:
            transformer = transform_messages_response
        restored = await _transform_committed(
            runtime, Direction.TO_LOCAL, payload, transformer, commit=not count_only
        )
    except (MessagesTransformError, MessagesRuntimeError, httpx.RequestError):
        return PlainTextResponse("Protected upstream response rejected.", status_code=502)
    finally:
        await upstream_response.aclose()

    response = Response(content=restored, status_code=upstream_response.status_code)
    response.raw_headers = list(_rewritten_response_headers(upstream_response.headers.raw))
    return response


async def _bounded_request_body(
    request: Request,
    *,
    reason: str = "responses-json-size-invalid",
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > _MAX_TRANSFORMED_RESPONSE_BYTES:
            raise ResponsesRuntimeError(reason)
        chunks.append(chunk)
    return b"".join(chunks)


async def _bounded_response_body(
    response: httpx.Response,
    *,
    reason: str = "responses-response-too-large",
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > _MAX_TRANSFORMED_RESPONSE_BYTES:
            raise ResponsesRuntimeError(reason)
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


def _is_structured_media_type(media_type: str) -> bool:
    return (
        media_type in {"text/event-stream", "application/json"}
        or media_type.endswith("+json")
    )


def _safe_unstructured_error(upstream_response: httpx.Response) -> Response:
    response = PlainTextResponse(
        "Upstream returned an error.", status_code=upstream_response.status_code
    )
    excluded = {b"content-type", b"content-length", b"content-encoding"}
    response.raw_headers.extend(
        (name, value)
        for name, value in filter_response_headers(upstream_response.headers.raw)
        if name.lower() not in excluded
    )
    return response


def _safe_empty_response(upstream_response: httpx.Response) -> Response:
    response = Response(status_code=upstream_response.status_code)
    excluded = {b"content-type", b"content-length", b"content-encoding"}
    response.raw_headers = [
        (name, value)
        for name, value in filter_response_headers(upstream_response.headers.raw)
        if name.lower() not in excluded
    ]
    return response


async def _transform_committed(
    runtime: PrivacyRuntime,
    direction: Direction,
    payload: bytes,
    transform: Callable[[bytes, Callable[[str, ContentKind], str]], bytes],
    *,
    bind_identity: Callable[[], None] | None = None,
    commit: bool = True,
) -> bytes:
    async with runtime.request_lock:
        for attempt in range(8):
            transaction = runtime.transaction(direction)
            transformed = transform(payload, transaction.transform)
            if bind_identity is not None:
                bind_identity()
            if not commit:
                return transformed
            try:
                transaction.commit()
                return transformed
            except PrivacyRuntimeError as error:
                if error.reason != "stale-vault-write" or attempt == 7:
                    raise
    raise PrivacyRuntimeError("stale-vault-write")
