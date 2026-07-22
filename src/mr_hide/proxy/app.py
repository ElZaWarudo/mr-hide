"""Starlette application factory for the loopback forwarding core."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx
from starlette.applications import Starlette

from mr_hide.protocols.responses.handler import ResponsesRuntime
from mr_hide.proxy.routes import proxy_routes

HttpClientFactory = Callable[[], httpx.AsyncClient]


class ProxyConfigurationError(ValueError):
    """Raised when proxy configuration could alter or expose the upstream boundary."""


def validate_upstream_url(value: str) -> str:
    """Validate the shared CLI/runtime upstream boundary without echoing its value."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
        httpx.URL(value)
    except (httpx.InvalidURL, UnicodeError, ValueError) as error:
        raise ProxyConfigurationError(
            "The upstream must be a valid HTTP(S) URL without userinfo or a fragment."
        ) from error
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or any(character.isspace() for character in parsed.hostname)
        or port == 0
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ProxyConfigurationError(
            "The upstream must be an HTTP(S) URL without userinfo or a fragment."
        )
    return value


def _default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0),
    )


def create_proxy_app(
    upstream: str,
    *,
    client_factory: HttpClientFactory = _default_client,
    responses_runtime: ResponsesRuntime | None = None,
) -> Starlette:
    """Create one proxy instance with a lifespan-scoped upstream client."""

    upstream_url = httpx.URL(validate_upstream_url(upstream))

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with client_factory() as client:
            app.state.http_client = client
            app.state.upstream_url = upstream_url
            app.state.responses_runtime = responses_runtime
            yield

    return Starlette(routes=proxy_routes(), lifespan=lifespan)
