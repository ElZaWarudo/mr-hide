"""Conversation-scoped OpenAI Responses runtime composition."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.detection import Detector
from mr_hide.protocols.responses.json_body import MAX_JSON_BYTES, ResponsesTransformError
from mr_hide.runtime.privacy import PrivacyRuntime, PrivacyRuntimeError, PrivacyTransaction
from mr_hide.state.bindings import BindingRegistry
from mr_hide.state.repository import VaultRepository

ResponsesRuntimeError = PrivacyRuntimeError
ResponsesTransaction = PrivacyTransaction


class ResponsesRuntime(PrivacyRuntime):
    """Bind one launched Codex process to exactly one encrypted conversation."""

    def __init__(
        self,
        *,
        client: str = "codex",
        conversation_id: UUID,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        native_identity: str | None,
        bypassed: bool,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__(
            client=client,
            conversation_id=conversation_id,
            repository=repository,
            registry=registry,
            detector=detector,
            policy=policy,
            native_identity=native_identity,
            bypassed=bypassed,
            clock=clock,
        )

    @classmethod
    def prepare(
        cls,
        *,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        resume_identity: str | None,
        bypass: bool = False,
        bypass_warning_accepted: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        identifier_factory: Callable[[], UUID] = uuid4,
    ) -> ResponsesRuntime:
        return super()._prepare(
            client="codex",
            repository=repository,
            registry=registry,
            detector=detector,
            policy=policy,
            resume_identity=resume_identity,
            bypass=bypass,
            bypass_warning_accepted=bypass_warning_accepted,
            clock=clock,
            identifier_factory=identifier_factory,
        )

    def bind_request_identity(self, original_payload: bytes) -> None:
        identity = _prompt_cache_key(original_payload)
        self.bind_native_identity(identity)


def _prompt_cache_key(payload: bytes) -> str:
    if not payload or len(payload) > MAX_JSON_BYTES:
        raise ResponsesRuntimeError("native-identity-missing")
    try:
        document = json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except ResponsesTransformError as error:
        raise ResponsesRuntimeError(error.reason) from None
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError):
        raise ResponsesRuntimeError("native-identity-missing") from None
    if not isinstance(document, dict):
        raise ResponsesRuntimeError("native-identity-missing")
    value = document.get("prompt_cache_key")
    if not isinstance(value, str):
        raise ResponsesRuntimeError("native-identity-missing")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ResponsesTransformError("responses-json-duplicate-key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise ResponsesTransformError("responses-json-invalid")
