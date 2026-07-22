from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from mr_hide.proxy.app import ProxyConfigurationError, create_proxy_app
from mr_hide.proxy.forwarding import ProxyTargetError, build_upstream_url
from tests.fixtures.upstream_app import RecordingTransport, TrackedByteStream, client_factory


@pytest.mark.asyncio
async def test_declared_route_preserves_request_and_response_contract() -> None:
    stream = TrackedByteStream((b'{"ok":', b"true}"))

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            207,
            headers=[
                (b"content-type", b"application/json"),
                (b"connection", b"x-private-hop"),
                (b"x-private-hop", b"do-not-forward"),
                (b"set-cookie", b"a=1"),
                (b"set-cookie", b"b=2"),
                (b"x-upstream", b"preserved"),
            ],
            stream=stream,
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test/base?api-version=2026-01-01",
        client_factory=client_factory(transport),
    )
    body = b'{"unknown":{"nested":true}}'

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
        ) as client,
    ):
        response = await client.post(
            "/v1/responses?z=last&a=%2F&a=two",
            headers={
                "connection": "x-private-hop",
                "x-private-hop": "do-not-forward",
                "x-custom": "preserved",
            },
            content=body,
        )

    assert response.status_code == 207
    assert response.content == b'{"ok":true}'
    assert response.headers["x-upstream"] == "preserved"
    assert response.headers.get_list("set-cookie") == ["a=1", "b=2"]
    assert "connection" not in response.headers
    assert "x-private-hop" not in response.headers
    assert stream.closed

    [captured] = transport.requests
    assert captured.method == "POST"
    assert captured.url == (
        "https://upstream.test/base/v1/responses?"
        "api-version=2026-01-01&z=last&a=%2F&a=two"
    )
    assert captured.chunks == (body, b"")
    assert (b"x-custom", b"preserved") in captured.headers
    assert not any(name.lower() == b"x-private-hop" for name, _ in captured.headers)
    assert not any(
        name.lower() == b"host" and value == b"127.0.0.1"
        for name, value in captured.headers
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ("/v1/responses", "/v1/messages", "/v1/messages/count_tokens"),
)
async def test_only_declared_post_routes_reach_upstream(path: str) -> None:
    transport = RecordingTransport(
        lambda request: httpx.Response(
            204,
            stream=TrackedByteStream(()),
            request=request,
        )
    )
    app = create_proxy_app(
        "http://upstream.test",
        client_factory=client_factory(transport),
    )

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
        ) as client,
    ):
        response = await client.post(path)
        missing = await client.post("/v1/models")
        wrong_method = await client.get(path)

    assert response.status_code == 204
    assert missing.status_code == 404
    assert wrong_method.status_code == 405
    assert len(transport.requests) == 1
    assert transport.requests[0].url == f"http://upstream.test{path}"


@pytest.mark.parametrize(
    "upstream",
    (
        "ftp://upstream.test",
        "http://user:secret@upstream.test",
        "https://upstream.test/#fragment",
        "//upstream.test",
    ),
)
def test_invalid_upstream_is_rejected(upstream: str) -> None:
    with pytest.raises(ProxyConfigurationError):
        create_proxy_app(upstream)


def test_absolute_form_request_target_is_rejected() -> None:
    with pytest.raises(ProxyTargetError):
        build_upstream_url(
            httpx.URL("https://upstream.test"),
            b"http://attacker.test/v1/responses",
            b"",
        )


@pytest.mark.asyncio
async def test_request_body_is_forwarded_as_chunks_without_ambient_proxy_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://PROXY_SENTINEL.invalid")
    monkeypatch.setenv("HTTPS_PROXY", "http://PROXY_SENTINEL.invalid")
    transport = RecordingTransport(
        lambda request: httpx.Response(
            200,
            stream=TrackedByteStream((b"ok",)),
            request=request,
        )
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
    )

    async def chunks() -> AsyncIterator[bytes]:
        yield b"first"
        yield b"second"

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1",
        ) as client,
    ):
        response = await client.post("/v1/responses", content=chunks())

    assert response.content == b"ok"
    assert transport.requests[0].chunks == (b"first", b"second", b"")
    assert "PROXY_SENTINEL" not in transport.requests[0].url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status"),
    (
        (httpx.ReadTimeout("fixture timeout"), 504),
        (httpx.ConnectError("fixture refused"), 502),
    ),
)
async def test_upstream_failures_are_safe(error: Exception, status: int) -> None:
    class FailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise error

    app = create_proxy_app(
        "http://upstream.test",
        client_factory=client_factory(FailingTransport()),
    )

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://127.0.0.1",
        ) as client,
    ):
        response = await client.post("/v1/responses", content=b"BODY_SENTINEL")

    assert response.status_code == status
    assert "BODY_SENTINEL" not in response.text
    assert "fixture" not in response.text
