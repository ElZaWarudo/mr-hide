"""Conversation-scoped OpenAI Responses runtime composition."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mr_hide.policy import (
    ContentKind,
    Direction,
    PolicyAction,
    ToolPolicy,
    decide_policy,
)
from mr_hide.privacy.detection import Detector
from mr_hide.privacy.mapping import restore_text, transform_text
from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.protocols.responses.json_body import MAX_JSON_BYTES, ResponsesTransformError
from mr_hide.state.bindings import BindingRegistry
from mr_hide.state.lifecycle import RETENTION_PERIOD, ConversationService, ConversationStatus
from mr_hide.state.models import ConversationState, VaultError, require_utc
from mr_hide.state.repository import VaultRepository


class ResponsesRuntimeError(RuntimeError):
    """Safe, stable failure at the state/protocol composition boundary."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ResponsesRuntime:
    """Bind one launched Codex process to exactly one encrypted conversation."""

    def __init__(
        self,
        *,
        conversation_id: UUID,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        native_identity: str | None,
        bypassed: bool,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.conversation_id = conversation_id
        self._repository = repository
        self._registry = registry
        self._detector = detector
        self.policy = policy
        self.bypassed = bypassed
        self._native_identity = native_identity
        self._clock = clock
        self._identity_lock = threading.Lock()

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
        service = ConversationService(repository, clock=clock)
        expected_mode = decide_policy(
            policy,
            Direction.TO_PROVIDER,
            ContentKind.CONVERSATION,
        ).substitution_mode
        if resume_identity is None:
            conversation_id = identifier_factory()
            state = ConversationState.new(
                conversation_id,
                mode=expected_mode,
                now=clock(),
            )
            result = service.create(state)
        else:
            bound_conversation = registry.lookup("codex", resume_identity)
            if bound_conversation is None:
                raise ResponsesRuntimeError("native-binding-missing")
            conversation_id = bound_conversation
            try:
                bound_state = repository.load(conversation_id)
            except VaultError as error:
                raise ResponsesRuntimeError(error.reason) from None
            if bound_state.mode is not expected_mode:
                raise ResponsesRuntimeError("policy-mode-mismatch")
            result = service.resume(conversation_id)
        if result.status not in {ConversationStatus.PROTECTED, ConversationStatus.BYPASSED}:
            raise ResponsesRuntimeError(result.reason or "conversation-unavailable")
        if bypass and result.status is not ConversationStatus.BYPASSED:
            result = service.accept_bypass(
                conversation_id,
                warning_accepted=bypass_warning_accepted,
            )
            if result.status is not ConversationStatus.BYPASSED:
                raise ResponsesRuntimeError(result.reason or "conversation-unavailable")
        return cls(
            conversation_id=conversation_id,
            repository=repository,
            registry=registry,
            detector=detector,
            policy=policy,
            native_identity=resume_identity,
            bypassed=result.status is ConversationStatus.BYPASSED,
            clock=clock,
        )

    def bind_request_identity(self, original_payload: bytes) -> None:
        identity = _prompt_cache_key(original_payload)
        with self._identity_lock:
            if self._native_identity is not None and identity != self._native_identity:
                raise ResponsesRuntimeError("native-binding-mismatch")
            self._registry.bind("codex", identity, self.conversation_id)
            self._native_identity = identity

    def transaction(self, direction: Direction) -> ResponsesTransaction:
        try:
            state = self._repository.load(self.conversation_id)
            now = require_utc(self._clock())
        except VaultError as error:
            raise ResponsesRuntimeError(error.reason) from None
        if now - state.last_activity >= RETENTION_PERIOD:
            raise ResponsesRuntimeError("expired")
        return ResponsesTransaction(
            repository=self._repository,
            state=state,
            detector=self._detector,
            policy=self.policy,
            direction=direction,
            now=now,
        )


class ResponsesTransaction:
    """Stage a complete body/stream against one mapping snapshot, then commit once."""

    def __init__(
        self,
        *,
        repository: VaultRepository,
        state: ConversationState,
        detector: Detector,
        policy: ToolPolicy,
        direction: Direction,
        now: datetime,
    ) -> None:
        self._repository = repository
        self._state = state
        self._detector = detector
        self._policy = policy
        self._direction = direction
        self._now = now
        self._mappings = state.mappings
        self._committed = False
        self.warning_codes: set[str] = set()

    def transform(self, text: str, kind: ContentKind) -> str:
        if self._committed:
            raise ResponsesRuntimeError("transaction-already-committed")
        if self._state.bypassed:
            return text
        try:
            decision = decide_policy(self._policy, self._direction, kind)
            if decision.warning_code is not None:
                self.warning_codes.add(decision.warning_code)
            if decision.action is PolicyAction.PASS_THROUGH:
                return text
            if decision.action is PolicyAction.RESTORE_KNOWN:
                return restore_text(text, self._mappings)
            if decision.substitution_mode is not self._state.mode:
                raise ResponsesRuntimeError("policy-mode-mismatch")
            detections = self._detector.detect(text)
            transformed = transform_text(
                text,
                detections,
                self._mappings,
                mode=decision.substitution_mode,
            )
            self._mappings = transformed.mappings
            return transformed.text
        except PrivacyProcessingError as error:
            raise ResponsesRuntimeError(error.reason) from None
        except ResponsesRuntimeError:
            raise
        except Exception:
            raise ResponsesRuntimeError("privacy-processing-failed") from None

    def commit(self) -> None:
        if self._committed:
            raise ResponsesRuntimeError("transaction-already-committed")
        try:
            updated = self._state.next_revision(
                mappings=self._mappings,
                last_activity=self._now,
            )
            self._repository.save(updated, expected_revision=self._state.revision)
        except VaultError as error:
            raise ResponsesRuntimeError(error.reason) from None
        self._committed = True


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
