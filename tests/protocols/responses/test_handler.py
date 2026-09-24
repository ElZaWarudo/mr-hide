from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.responses import ResponsesRuntime, ResponsesRuntimeError
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


def runtime(tmp_path: Path, policy: ToolPolicy = ToolPolicy.DEFAULT) -> tuple[
    ResponsesRuntime, VaultRepository, BindingRegistry
]:
    repository = VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())
    registry = BindingRegistry(tmp_path)
    prepared = ResponsesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=policy,
        resume_identity=None,
        identifier_factory=lambda: CONVERSATION_ID,
    )
    return prepared, repository, registry


@pytest.mark.asyncio
async def test_json_round_trip_binds_identity_and_commits_once_per_body(tmp_path: Path) -> None:
    prepared, repository, registry = runtime(tmp_path)

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "999"},
            stream=TrackedByteStream(
                (json.dumps({"output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "Hello <P0>"}
                ]}], "usage": {"total_tokens": 7}}).encode(),)
            ),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    body = {
        "prompt_cache_key": NATIVE_ID,
        "input": "Ask Alice",
        "metadata": {"opaque": "Alice"},
    }

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post("/v1/responses", json=body)

    assert response.status_code == 200
    assert response.json()["output"][0]["content"][0]["text"] == "Hello Alice"
    assert response.json()["usage"] == {"total_tokens": 7}
    [captured] = transport.requests
    forwarded = json.loads(b"".join(captured.chunks))
    assert forwarded["input"] == "Ask <P0>"
    assert forwarded["metadata"] == {"opaque": "Alice"}
    assert registry.lookup("codex", NATIVE_ID) == CONVERSATION_ID
    assert repository.load(CONVERSATION_ID).revision == 2
    assert response.headers.get("content-length") != "999"


@pytest.mark.asyncio
async def test_plain_upstream_rate_limit_keeps_status_without_exposing_body(tmp_path: Path) -> None:
    prepared, _repository, _registry = runtime(tmp_path)
    transport = RecordingTransport(
        lambda request: httpx.Response(
            429,
            headers={"content-type": "text/plain", "retry-after": "3"},
            content=b"upstream private diagnostic",
            request=request,
        )
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/responses", json={"prompt_cache_key": NATIVE_ID, "input": "Alice"}
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "3"
    assert b"private diagnostic" not in response.content


@pytest.mark.asyncio
async def test_empty_upstream_success_keeps_no_content_status(tmp_path: Path) -> None:
    prepared, _repository, _registry = runtime(tmp_path)
    transport = RecordingTransport(
        lambda request: httpx.Response(204, request=request)
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/responses", json={"prompt_cache_key": NATIVE_ID, "input": "Alice"}
        )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_default_tool_data_passes_through_while_conversation_is_protected(
    tmp_path: Path,
) -> None:
    prepared, _repository, _registry = runtime(tmp_path)

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=TrackedByteStream((b'{"output":[]}',)),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    body = {
        "prompt_cache_key": NATIVE_ID,
        "input": "Alice",
        "tools": [{"type": "function", "name": "Alice", "description": "Alice"}],
    }
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post("/v1/responses", json=body)

    assert response.status_code == 200
    forwarded = json.loads(b"".join(transport.requests[0].chunks))
    assert forwarded["input"] == "<P0>"
    assert forwarded["tools"] == body["tools"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy",
    (ToolPolicy.SAFE_TOOL_CALLS, ToolPolicy.TOOL_COMPATIBILITY),
)
async def test_protective_tool_policies_remove_originals_from_tool_data(
    tmp_path: Path,
    policy: ToolPolicy,
) -> None:
    prepared, _repository, _registry = runtime(tmp_path, policy)

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=TrackedByteStream((b'{"output":[]}',)),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/responses",
            json={
                "prompt_cache_key": NATIVE_ID,
                "input": "Alice",
                "tools": [{"type": "function", "name": "Alice"}],
            },
        )

    assert response.status_code == 200
    assert b"Alice" not in b"".join(transport.requests[0].chunks)


@pytest.mark.asyncio
async def test_sse_restores_only_after_complete_stream(tmp_path: Path) -> None:
    prepared, _repository, _registry = runtime(tmp_path)
    events = (
        {
            "type": "response.output_text.delta",
            "item_id": "message",
            "output_index": 0,
            "content_index": 0,
            "delta": "Hello <P0>",
        },
        {
            "type": "response.output_text.done",
            "item_id": "message",
            "output_index": 0,
            "content_index": 0,
            "text": "Hello <P0>",
        },
    )
    sse = b"".join(
        f"data: {json.dumps(event, separators=(',', ':'))}\n\n".encode()
        for event in events
    )

    def response_factory(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=TrackedByteStream((sse[:17], sse[17:])),
            request=request,
        )

    transport = RecordingTransport(response_factory)
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        response = await client.post(
            "/v1/responses",
            json={"prompt_cache_key": NATIVE_ID, "input": "Alice"},
        )

    assert response.status_code == 200
    assert "Hello Alice" in response.text
    assert "<P0>" not in response.text


@pytest.mark.asyncio
async def test_invalid_body_or_binding_never_reaches_upstream(tmp_path: Path) -> None:
    prepared, repository, _registry = runtime(tmp_path)
    prepared.bind_request_identity(
        json.dumps({"prompt_cache_key": NATIVE_ID}).encode()
    )
    transport = RecordingTransport(
        lambda request: httpx.Response(200, content=b'{"output":[]}', request=request)
    )
    app = create_proxy_app(
        "https://upstream.test",
        client_factory=client_factory(transport),
        responses_runtime=prepared,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as client,
    ):
        malformed = await client.post("/v1/responses", content=b'{"input":"Alice"}')
        mismatch = await client.post(
            "/v1/responses",
            json={
                "prompt_cache_key": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "input": "Alice",
            },
        )

    assert malformed.status_code == 400
    assert mismatch.status_code == 400
    assert transport.requests == []
    state = repository.load(CONVERSATION_ID)
    assert state.revision == 0
    assert state.mappings.records == ()


def test_resume_uses_bound_conversation_and_expired_binding_is_rejected(
    tmp_path: Path,
) -> None:
    repository = VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())
    registry = BindingRegistry(tmp_path)
    started = datetime(2026, 7, 22, 12, tzinfo=UTC)
    prepared = ResponsesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=None,
        clock=lambda: started,
        identifier_factory=lambda: CONVERSATION_ID,
    )
    prepared.bind_request_identity(
        json.dumps({"prompt_cache_key": NATIVE_ID}).encode()
    )

    resumed = ResponsesRuntime.prepare(
        repository=repository,
        registry=registry,
        detector=AliceDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=NATIVE_ID,
        clock=lambda: started + timedelta(days=29),
    )

    assert resumed.conversation_id == CONVERSATION_ID
    revision_before_mismatch = repository.load(CONVERSATION_ID).revision
    with pytest.raises(ResponsesRuntimeError, match="policy-mode-mismatch"):
        ResponsesRuntime.prepare(
            repository=repository,
            registry=registry,
            detector=AliceDetector(),
            policy=ToolPolicy.TOOL_COMPATIBILITY,
            resume_identity=NATIVE_ID,
            clock=lambda: started + timedelta(days=29),
        )
    assert repository.load(CONVERSATION_ID).revision == revision_before_mismatch
    with pytest.raises(ResponsesRuntimeError, match="expired"):
        ResponsesRuntime.prepare(
            repository=repository,
            registry=registry,
            detector=AliceDetector(),
            policy=ToolPolicy.DEFAULT,
            resume_identity=NATIVE_ID,
            clock=lambda: started + timedelta(days=60),
        )
