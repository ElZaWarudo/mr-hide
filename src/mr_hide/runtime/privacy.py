"""Provider-neutral encrypted conversation transactions."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from mr_hide.policy import ContentKind, Direction, PolicyAction, ToolPolicy, decide_policy
from mr_hide.privacy.detection import Detector
from mr_hide.privacy.mapping import restore_text, transform_text
from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.state.bindings import BindingRegistry
from mr_hide.state.lifecycle import RETENTION_PERIOD, ConversationService, ConversationStatus
from mr_hide.state.models import ConversationState, VaultError, require_utc
from mr_hide.state.repository import VaultRepository


class PrivacyRuntimeError(RuntimeError):
    """Safe, stable failure at the state/protocol composition boundary."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class PrivacyRuntime:
    """Own one native-client binding and its encrypted conversation."""

    def __init__(
        self,
        *,
        client: str,
        conversation_id: UUID,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        native_identity: str | None,
        bypassed: bool,
        clock: Callable[[], datetime],
    ) -> None:
        self.client = client
        self.conversation_id = conversation_id
        self._repository = repository
        self._registry = registry
        self._detector = detector
        self.policy = policy
        self.native_identity = native_identity
        self.bypassed = bypassed
        self._clock = clock
        self._identity_lock = threading.Lock()

    @classmethod
    def _prepare(
        cls,
        *,
        client: str,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        resume_identity: str | None,
        new_native_identity: str | None = None,
        bypass: bool = False,
        bypass_warning_accepted: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        identifier_factory: Callable[[], UUID] = uuid4,
    ) -> Self:
        service = ConversationService(repository, clock=clock)
        expected_mode = decide_policy(
            policy, Direction.TO_PROVIDER, ContentKind.CONVERSATION
        ).substitution_mode
        if resume_identity is None:
            conversation_id = identifier_factory()
            result = service.create(
                ConversationState.new(conversation_id, mode=expected_mode, now=clock())
            )
            native_identity = new_native_identity
        else:
            try:
                bound_conversation = registry.lookup(client, resume_identity)
            except VaultError as error:
                raise PrivacyRuntimeError(error.reason) from None
            if bound_conversation is None:
                raise PrivacyRuntimeError("native-binding-missing")
            conversation_id = bound_conversation
            try:
                bound_state = repository.load(conversation_id)
            except VaultError as error:
                raise PrivacyRuntimeError(error.reason) from None
            if bound_state.mode is not expected_mode:
                raise PrivacyRuntimeError("policy-mode-mismatch")
            result = service.resume(conversation_id)
            native_identity = resume_identity
        if result.status not in {ConversationStatus.PROTECTED, ConversationStatus.BYPASSED}:
            raise PrivacyRuntimeError(result.reason or "conversation-unavailable")
        if bypass and result.status is not ConversationStatus.BYPASSED:
            result = service.accept_bypass(
                conversation_id, warning_accepted=bypass_warning_accepted
            )
            if result.status is not ConversationStatus.BYPASSED:
                raise PrivacyRuntimeError(result.reason or "conversation-unavailable")
        if resume_identity is None and native_identity is not None:
            try:
                registry.bind(client, native_identity, conversation_id)
            except VaultError as error:
                raise PrivacyRuntimeError(error.reason) from None
        return cls(
            client=client,
            conversation_id=conversation_id,
            repository=repository,
            registry=registry,
            detector=detector,
            policy=policy,
            native_identity=native_identity,
            bypassed=result.status is ConversationStatus.BYPASSED,
            clock=clock,
        )

    def bind_native_identity(self, identity: str) -> None:
        with self._identity_lock:
            if self.native_identity is not None and identity != self.native_identity:
                raise PrivacyRuntimeError("native-binding-mismatch")
            try:
                self._registry.bind(self.client, identity, self.conversation_id)
            except VaultError as error:
                raise PrivacyRuntimeError(error.reason) from None
            self.native_identity = identity

    def transaction(self, direction: Direction) -> PrivacyTransaction:
        try:
            state = self._repository.load(self.conversation_id)
            now = require_utc(self._clock())
        except VaultError as error:
            raise PrivacyRuntimeError(error.reason) from None
        if now - state.last_activity >= RETENTION_PERIOD:
            raise PrivacyRuntimeError("expired")
        return PrivacyTransaction(
            repository=self._repository,
            state=state,
            detector=self._detector,
            policy=self.policy,
            direction=direction,
            now=now,
        )


class PrivacyTransaction:
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
            raise PrivacyRuntimeError("transaction-already-committed")
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
                raise PrivacyRuntimeError("policy-mode-mismatch")
            detections = self._detector.detect(text)
            transformed = transform_text(
                text, detections, self._mappings, mode=decision.substitution_mode
            )
            self._mappings = transformed.mappings
            return transformed.text
        except PrivacyProcessingError as error:
            raise PrivacyRuntimeError(error.reason) from None
        except PrivacyRuntimeError:
            raise
        except Exception:
            raise PrivacyRuntimeError("privacy-processing-failed") from None

    def commit(self) -> None:
        if self._committed:
            raise PrivacyRuntimeError("transaction-already-committed")
        try:
            updated = self._state.next_revision(mappings=self._mappings, last_activity=self._now)
            self._repository.save(updated, expected_revision=self._state.revision)
        except VaultError as error:
            raise PrivacyRuntimeError(error.reason) from None
        self._committed = True
