"""Conversation-scoped retention, bypass, and privacy operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from mr_hide.policy import PolicyAction, PolicyDecision
from mr_hide.privacy.mapping import MappingTable, restore_text, transform_text
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError
from mr_hide.state.models import ConversationState, VaultError, parse_conversation_id, require_utc
from mr_hide.state.repository import VaultRepository

RETENTION_PERIOD = timedelta(days=30)


class ConversationStatus(StrEnum):
    PROTECTED = "protected"
    BYPASSED = "bypassed"
    BLOCKED = "blocked"
    MISSING = "missing"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class ConversationResult:
    status: ConversationStatus
    conversation_id: UUID
    text: str | None = None
    reason: str | None = None
    warning_code: str | None = None

    def __post_init__(self) -> None:
        if self.status is ConversationStatus.BLOCKED and self.text is not None:
            raise ValueError("blocked results cannot contain text")


class ConversationService:
    def __init__(
        self,
        repository: VaultRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._clock = clock

    def create(self, state: ConversationState) -> ConversationResult:
        try:
            self._repository.create(state)
        except VaultError as error:
            return ConversationResult(
                ConversationStatus.BLOCKED,
                state.conversation_id,
                reason=error.reason,
            )
        return ConversationResult(ConversationStatus.PROTECTED, state.conversation_id)

    def resume(self, conversation_id: str | UUID) -> ConversationResult:
        parsed = parse_conversation_id(conversation_id)
        state = self._load_or_status(parsed)
        if isinstance(state, ConversationResult):
            return state
        now = self._now()
        if self._is_expired(state, now):
            if self._repository.delete_if_inactive(
                parsed,
                inactive_since=now - RETENTION_PERIOD,
            ):
                return ConversationResult(ConversationStatus.EXPIRED, parsed, reason="expired")
            state = self._load_or_status(parsed)
            if isinstance(state, ConversationResult):
                return state
        try:
            updated = state.next_revision(last_activity=now)
            self._repository.save(updated, expected_revision=state.revision)
        except VaultError as error:
            return ConversationResult(
                ConversationStatus.BLOCKED,
                parsed,
                reason=error.reason,
            )
        return ConversationResult(
            ConversationStatus.BYPASSED if updated.bypassed else ConversationStatus.PROTECTED,
            parsed,
            warning_code="conversation-bypass-active" if updated.bypassed else None,
        )

    def accept_bypass(
        self,
        conversation_id: str | UUID,
        *,
        warning_accepted: bool,
    ) -> ConversationResult:
        parsed = parse_conversation_id(conversation_id)
        if not warning_accepted:
            return ConversationResult(
                ConversationStatus.BLOCKED,
                parsed,
                reason="bypass-warning-not-accepted",
            )
        state = self._load_active(parsed)
        if isinstance(state, ConversationResult):
            return state
        try:
            updated = state.next_revision(bypassed=True, last_activity=self._now())
            self._repository.save(updated, expected_revision=state.revision)
        except VaultError as error:
            return ConversationResult(ConversationStatus.BLOCKED, parsed, reason=error.reason)
        return ConversationResult(
            ConversationStatus.BYPASSED,
            parsed,
            warning_code="conversation-bypass-active",
        )

    def process(
        self,
        conversation_id: str | UUID,
        text: str,
        detections: tuple[DetectedSpan, ...],
        decision: PolicyDecision,
    ) -> ConversationResult:
        parsed = parse_conversation_id(conversation_id)
        state = self._load_active(parsed)
        if isinstance(state, ConversationResult):
            return state
        if state.bypassed:
            return self._commit_text(
                state,
                text,
                status=ConversationStatus.BYPASSED,
                warning_code="conversation-bypass-active",
            )
        if (
            decision.action is PolicyAction.PROTECT
            and decision.substitution_mode is not state.mode
        ):
            return ConversationResult(
                ConversationStatus.BLOCKED,
                parsed,
                reason="policy-mode-mismatch",
            )
        try:
            if decision.action is PolicyAction.PROTECT:
                transformed = transform_text(
                    text,
                    detections,
                    state.mappings,
                    mode=decision.substitution_mode,
                )
                output = transformed.text
                mappings = transformed.mappings
            elif decision.action is PolicyAction.RESTORE_KNOWN:
                output = restore_text(text, state.mappings)
                mappings = state.mappings
            else:
                output = text
                mappings = state.mappings
        except PrivacyProcessingError as error:
            return ConversationResult(
                ConversationStatus.BLOCKED,
                parsed,
                reason=error.reason,
            )
        return self._commit_text(
            state,
            output,
            mappings=mappings,
            status=ConversationStatus.PROTECTED,
            warning_code=decision.warning_code,
        )

    def cleanup_expired(self) -> int:
        cutoff = self._now() - RETENTION_PERIOD
        deleted = 0
        for conversation_id in self._repository.conversation_ids():
            try:
                if self._repository.delete_if_inactive(
                    conversation_id,
                    inactive_since=cutoff,
                ):
                    deleted += 1
            except VaultError:
                # A damaged, unrelated vault must not block healthy conversations.
                continue
        return deleted

    def _commit_text(
        self,
        state: ConversationState,
        text: str,
        *,
        mappings: MappingTable | None = None,
        status: ConversationStatus,
        warning_code: str | None = None,
    ) -> ConversationResult:
        try:
            updated = state.next_revision(
                mappings=state.mappings if mappings is None else mappings,
                last_activity=self._now(),
            )
            self._repository.save(updated, expected_revision=state.revision)
        except VaultError as error:
            return ConversationResult(
                ConversationStatus.BLOCKED,
                state.conversation_id,
                reason=error.reason,
            )
        return ConversationResult(
            status,
            state.conversation_id,
            text=text,
            warning_code=warning_code,
        )

    def _load_active(self, conversation_id: UUID) -> ConversationState | ConversationResult:
        state = self._load_or_status(conversation_id)
        if isinstance(state, ConversationResult):
            return state
        now = self._now()
        if self._is_expired(state, now):
            try:
                deleted = self._repository.delete_if_inactive(
                    conversation_id,
                    inactive_since=now - RETENTION_PERIOD,
                )
            except VaultError as error:
                return ConversationResult(
                    ConversationStatus.BLOCKED,
                    conversation_id,
                    reason=error.reason,
                )
            if deleted:
                return ConversationResult(
                    ConversationStatus.EXPIRED,
                    conversation_id,
                    reason="expired",
                )
            return self._load_or_status(conversation_id)
        return state

    def _load_or_status(self, conversation_id: UUID) -> ConversationState | ConversationResult:
        try:
            return self._repository.load(conversation_id)
        except VaultError as error:
            if error.reason == "vault-missing":
                return ConversationResult(
                    ConversationStatus.MISSING,
                    conversation_id,
                    reason="missing",
                )
            return ConversationResult(
                ConversationStatus.BLOCKED,
                conversation_id,
                reason=error.reason,
            )

    def _now(self) -> datetime:
        return require_utc(self._clock())

    @staticmethod
    def _is_expired(state: ConversationState, now: datetime) -> bool:
        return now - state.last_activity >= RETENTION_PERIOD
