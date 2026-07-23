from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.messages import MessagesRuntime, MessagesRuntimeError
from mr_hide.proxy import create_proxy_app
from mr_hide.state import AtomicVaultStore, BindingRegistry, VaultRepository
from tests.fixtures.upstream_app import RecordingTransport, TrackedByteStream, client_factory
from tests.state.helpers import StaticKeyProvider

NATIVE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CONVERSATION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


class AliceDetector:
    def detect(self, text: str, **_kwargs: object) -> tuple[DetectedSpan, ...]:
        return tuple(
            DetectedSpan(index, index + 5, "PERSON", 1.0, "en", "fixture")
            for index in range(len(text))
            if text.startswith("Alice", index)
        )


def runtime(
    tmp_path: Path, policy: ToolPolicy = ToolPolicy.DEFAULT
) -> tuple[MessagesRuntime, VaultRepository, BindingRegistry]:
    repository = VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())
    registry = BindingRegistry(tmp_path)
    prepared = MessagesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=policy,
        resume_identity=None,
        identifier_factory=lambda: CONVERSATION_ID,
        native_identifier_factory=lambda: UUID(NATIVE_ID),
    )
    return prepared, repository, registry


@pytest.mark.asyncio
async def test_json_round_trip_uses_prebound_identity_and_commits_both_bodies(
    tmp_path: Path,
) -> None:
    prepared, repository, registry = runtime(tmp_path)

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "999"},
            stream=TrackedByteStream((b'{"content":[{"type":"text","text":"Hello <P0>"}]}',)),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    body = {
        "model": "claude-test",
        "messages": [{"role": "user", "content": "Ask Alice"}],
        "metadata": {"opaque": "Alice"},
    }
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post("/v1/messages", json=body)

    assert response.status_code == 200
    assert response.json()["content"][0]["text"] == "Hello Alice"
    forwarded = json.loads(b"".join(transport.requests[0].chunks))
    assert forwarded["messages"][0]["content"] == "Ask <P0>"
    assert forwarded["metadata"] == {"opaque": "Alice"}
    assert registry.lookup("claude", NATIVE_ID) == CONVERSATION_ID
    assert repository.load(CONVERSATION_ID).revision == 2
    assert response.headers.get("content-length") != "999"


@pytest.mark.asyncio
async def test_count_request_protects_text_without_response_state_mutation(
    tmp_path: Path,
) -> None:
    prepared, repository, _registry = runtime(tmp_path)
    transport = RecordingTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b'{"input_tokens":7}',
            request=request,
        )
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/messages/count_tokens",
            json={"messages": [{"role": "user", "content": "Alice"}]},
        )

    assert response.json() == {"input_tokens": 7}
    assert b"Alice" not in b"".join(transport.requests[0].chunks)
    assert repository.load(CONVERSATION_ID).revision == 1


@pytest.mark.asyncio
async def test_malformed_request_never_reaches_upstream(tmp_path: Path) -> None:
    prepared, repository, _registry = runtime(tmp_path)
    transport = RecordingTransport(
        lambda request: httpx.Response(200, content=b"{}", request=request)
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/messages", content=b'{"messages":[{"content":"Alice"}],"messages":[]}'
        )

    assert response.status_code == 400
    assert transport.requests == []
    assert repository.load(CONVERSATION_ID).revision == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", (ToolPolicy.SAFE_TOOL_CALLS, ToolPolicy.TOOL_COMPATIBILITY))
async def test_protective_tool_policies_remove_originals_end_to_end(
    tmp_path: Path, policy: ToolPolicy
) -> None:
    prepared, _repository, _registry = runtime(tmp_path, policy)
    transport = RecordingTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b'{"content":[]}',
            request=request,
        )
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/messages",
            json={
                "messages": [{"role": "user", "content": "Alice"}],
                "tools": [
                    {
                        "name": "lookup_Alice",
                        "description": "Find Alice",
                        "input_schema": {"type": "object", "title": "Alice"},
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert b"Alice" not in b"".join(transport.requests[0].chunks)


@pytest.mark.asyncio
async def test_default_policy_keeps_tool_data_visible_but_protects_conversation(
    tmp_path: Path,
) -> None:
    prepared, _repository, _registry = runtime(tmp_path)
    transport = RecordingTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b'{"content":[]}',
            request=request,
        )
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/messages",
            json={
                "messages": [{"role": "user", "content": "Alice"}],
                "tools": [{"name": "lookup_Alice", "description": "Find Alice"}],
            },
        )

    forwarded = json.loads(b"".join(transport.requests[0].chunks))
    assert response.status_code == 200
    assert forwarded["messages"][0]["content"] == "<P0>"
    assert forwarded["tools"][0]["name"] == "lookup_Alice"


@pytest.mark.asyncio
async def test_sse_text_restores_after_complete_block(tmp_path: Path) -> None:
    prepared, _repository, _registry = runtime(tmp_path)

    def frame(event: dict[str, object]) -> bytes:
        return (
            f"event: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"
        ).encode()

    stream = b"".join(
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
                    "delta": {"type": "text_delta", "text": "Hello <P0>"},
                }
            ),
            frame({"type": "content_block_stop", "index": 0}),
            frame({"type": "message_stop"}),
        )
    )

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=TrackedByteStream((stream[:19], stream[19:])),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        messages_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/messages",
            json={"messages": [{"role": "user", "content": "Alice"}]},
        )

    assert response.status_code == 200
    assert "Hello Alice" in response.text
    assert "<P0>" not in response.text


def test_new_and_explicit_resume_share_only_the_bound_vault(tmp_path: Path) -> None:
    repository = VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())
    registry = BindingRegistry(tmp_path)
    started = datetime(2026, 7, 22, 12, tzinfo=UTC)
    prepared = MessagesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=None,
        clock=lambda: started,
        identifier_factory=lambda: CONVERSATION_ID,
        native_identifier_factory=lambda: UUID(NATIVE_ID),
    )
    resumed = MessagesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=NATIVE_ID,
        clock=lambda: started + timedelta(days=29),
    )

    assert prepared.native_identity == NATIVE_ID
    assert resumed.conversation_id == CONVERSATION_ID
    with pytest.raises(MessagesRuntimeError, match="policy-mode-mismatch"):
        MessagesRuntime.prepare(
            repository=repository,
            registry=registry,
            detector=AliceDetector(),
            policy=ToolPolicy.TOOL_COMPATIBILITY,
            resume_identity=NATIVE_ID,
            clock=lambda: started + timedelta(days=29),
        )
    with pytest.raises(MessagesRuntimeError, match="expired"):
        MessagesRuntime.prepare(
            repository=repository,
            registry=registry,
            detector=AliceDetector(),
            policy=ToolPolicy.DEFAULT,
            resume_identity=NATIVE_ID,
            clock=lambda: started + timedelta(days=60),
        )
