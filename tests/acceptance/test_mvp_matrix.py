from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.messages import MessagesRuntime
from mr_hide.protocols.responses import ResponsesRuntime
from mr_hide.proxy import create_proxy_app
from mr_hide.state import AtomicVaultStore, BindingRegistry, VaultRepository
from tests.fixtures.upstream_app import RecordingTransport, client_factory
from tests.state.helpers import StaticKeyProvider

SOURCE = "alice@example.com"
NATIVE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class EmailDetector:
    def detect(self, text: str, **_kwargs: object) -> tuple[DetectedSpan, ...]:
        return tuple(
            DetectedSpan(index, index + len(SOURCE), "EMAIL_ADDRESS", 1.0, "en", "fixture")
            for index in range(len(text))
            if text.startswith(SOURCE, index)
        )


def prepare_runtime(
    tmp_path: Path,
    provider: str,
    policy: ToolPolicy,
    *,
    bypass: bool = False,
) -> ResponsesRuntime | MessagesRuntime:
    repository = VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())
    common = {
        "repository": repository,
        "registry": BindingRegistry(tmp_path),
        "detector": EmailDetector(),
        "policy": policy,
        "resume_identity": None,
        "bypass": bypass,
        "bypass_warning_accepted": bypass,
    }
    if provider == "responses":
        return ResponsesRuntime.prepare(**common)
    return MessagesRuntime.prepare(
        **common,
        native_identifier_factory=lambda: UUID(NATIVE_ID),
    )


def request_for(provider: str) -> tuple[str, dict[str, object]]:
    if provider == "responses":
        return (
            "/v1/responses?trace=two",
            {
                "prompt_cache_key": NATIVE_ID,
                "input": SOURCE,
                "tools": [
                    {"type": "function", "name": "lookup", "description": SOURCE}
                ],
                "future": {"opaque": "OPAQUE_SENTINEL"},
            },
        )
    return (
        "/v1/messages?trace=two",
        {
            "messages": [{"role": "user", "content": SOURCE}],
            "tools": [{"name": "lookup", "description": SOURCE}],
            "future": {"opaque": "OPAQUE_SENTINEL"},
        },
    )


def protected_conversation(provider: str, payload: dict[str, object]) -> str:
    if provider == "responses":
        value = payload["input"]
    else:
        messages = payload["messages"]
        assert isinstance(messages, list)
        value = messages[0]["content"]
    assert isinstance(value, str)
    return value


def response_for(provider: str, substitute: str) -> bytes:
    if provider == "responses":
        document = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": substitute}],
                }
            ],
            "future": {"opaque": "OPAQUE_SENTINEL"},
        }
    else:
        document = {
            "content": [{"type": "text", "text": substitute}],
            "future": {"opaque": "OPAQUE_SENTINEL"},
        }
    return json.dumps(document, separators=(",", ":")).encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ("responses", "messages"))
@pytest.mark.parametrize("policy", tuple(ToolPolicy))
async def test_cross_client_policy_composition_and_restoration(
    tmp_path: Path,
    provider: str,
    policy: ToolPolicy,
) -> None:
    runtime = prepare_runtime(tmp_path, provider, policy)
    transport: RecordingTransport

    def respond(request: httpx.Request) -> httpx.Response:
        forwarded = json.loads(b"".join(transport.requests[-1].chunks))
        substitute = protected_conversation(provider, forwarded)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=response_for(provider, substitute),
            request=request,
        )

    transport = RecordingTransport(respond)
    app = create_proxy_app(
        "https://upstream.test/gateway?tenant=one",
        client_factory=client_factory(transport),
        responses_runtime=runtime if isinstance(runtime, ResponsesRuntime) else None,
        messages_runtime=runtime if isinstance(runtime, MessagesRuntime) else None,
    )
    path, body = request_for(provider)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(path, json=body)

    forwarded_bytes = b"".join(transport.requests[0].chunks)
    forwarded = json.loads(forwarded_bytes)
    assert response.status_code == 200
    assert SOURCE in response.text
    assert protected_conversation(provider, forwarded) != SOURCE
    assert forwarded["future"] == {"opaque": "OPAQUE_SENTINEL"}
    assert response.json()["future"] == {"opaque": "OPAQUE_SENTINEL"}
    assert transport.requests[0].url.endswith(
        "/gateway/v1/responses?tenant=one&trace=two"
        if provider == "responses"
        else "/gateway/v1/messages?tenant=one&trace=two"
    )
    if policy is ToolPolicy.DEFAULT:
        assert SOURCE.encode() in forwarded_bytes
    else:
        assert SOURCE.encode() not in forwarded_bytes


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ("responses", "messages"))
async def test_malformed_requests_fail_before_composed_upstream(
    tmp_path: Path,
    provider: str,
) -> None:
    runtime = prepare_runtime(tmp_path, provider, ToolPolicy.DEFAULT)
    transport = RecordingTransport(
        lambda request: httpx.Response(200, content=b"{}", request=request)
    )
    app = create_proxy_app(
        "https://upstream.test/gateway",
        client_factory=client_factory(transport),
        responses_runtime=runtime if isinstance(runtime, ResponsesRuntime) else None,
        messages_runtime=runtime if isinstance(runtime, MessagesRuntime) else None,
    )
    path = "/v1/responses" if provider == "responses" else "/v1/messages"
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(path, content=b'{"duplicate":1,"duplicate":2}')

    assert response.status_code == 400
    assert transport.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ("responses", "messages"))
async def test_bypass_is_explicit_and_isolated_from_protected_runtime(
    tmp_path: Path,
    provider: str,
) -> None:
    protected = prepare_runtime(tmp_path / "protected", provider, ToolPolicy.DEFAULT)
    bypassed = prepare_runtime(
        tmp_path / "bypassed", provider, ToolPolicy.DEFAULT, bypass=True
    )
    captures: list[bytes] = []

    async def exercise(runtime: ResponsesRuntime | MessagesRuntime) -> None:
        transport: RecordingTransport

        def respond(request: httpx.Request) -> httpx.Response:
            payload = b"".join(transport.requests[-1].chunks)
            captures.append(payload)
            forwarded = json.loads(payload)
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=response_for(
                    provider, protected_conversation(provider, forwarded)
                ),
                request=request,
            )

        transport = RecordingTransport(respond)
        app = create_proxy_app(
            "https://upstream.test",
            client_factory=client_factory(transport),
            responses_runtime=runtime if isinstance(runtime, ResponsesRuntime) else None,
            messages_runtime=runtime if isinstance(runtime, MessagesRuntime) else None,
        )
        path, body = request_for(provider)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://local"
            ) as client,
        ):
            response = await client.post(path, json=body)
        assert response.status_code == 200

    await exercise(protected)
    await exercise(bypassed)

    assert SOURCE.encode() not in captures[0].split(b'"tools"', 1)[0]
    assert SOURCE.encode() in captures[1]
    assert protected.bypassed is False
    assert bypassed.bypassed is True
