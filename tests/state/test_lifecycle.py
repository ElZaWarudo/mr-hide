from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from mr_hide.policy import ContentKind, Direction, ToolPolicy, decide_policy
from mr_hide.privacy.mapping import SubstitutionMode
from mr_hide.privacy.models import DetectedSpan
from mr_hide.state import (
    RETENTION_PERIOD,
    AtomicVaultStore,
    ConversationService,
    ConversationState,
    ConversationStatus,
    VaultCodec,
    VaultError,
    VaultRepository,
)
from tests.state.helpers import CONVERSATION_ID, StaticKeyProvider

OTHER_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


def service(path: Path, clock: MutableClock) -> tuple[ConversationService, VaultRepository]:
    repository = VaultRepository(AtomicVaultStore(path), StaticKeyProvider(), VaultCodec())
    return ConversationService(repository, clock=clock), repository


def fresh_state(
    conversation_id: UUID,
    clock: MutableClock,
    *,
    mode: SubstitutionMode = SubstitutionMode.ALIAS,
) -> ConversationState:
    return ConversationState.new(conversation_id, mode=mode, now=clock())


def person_span(text: str) -> tuple[DetectedSpan, ...]:
    return (DetectedSpan(0, len(text), "PERSON", 1.0, "en", "test"),)


def test_resume_refreshes_before_boundary_and_expires_at_boundary(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))

    clock.value += RETENTION_PERIOD - timedelta(seconds=1)
    resumed = lifecycle.resume(CONVERSATION_ID)
    assert resumed.status is ConversationStatus.PROTECTED
    assert repository.load(CONVERSATION_ID).last_activity == clock.value

    clock.value += RETENTION_PERIOD
    expired = lifecycle.resume(CONVERSATION_ID)
    assert expired.status is ConversationStatus.EXPIRED
    assert lifecycle.resume(CONVERSATION_ID).status is ConversationStatus.MISSING


def test_bypass_requires_warning_and_is_isolated_visible_and_persistent(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, _repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    lifecycle.create(fresh_state(OTHER_ID, clock))

    refused = lifecycle.accept_bypass(CONVERSATION_ID, warning_accepted=False)
    accepted = lifecycle.accept_bypass(CONVERSATION_ID, warning_accepted=True)
    resumed = lifecycle.resume(CONVERSATION_ID)
    other = lifecycle.resume(OTHER_ID)

    assert refused.status is ConversationStatus.BLOCKED
    assert refused.text is None
    assert accepted.warning_code == "conversation-bypass-active"
    assert resumed.status is ConversationStatus.BYPASSED
    assert resumed.warning_code == "conversation-bypass-active"
    assert other.status is ConversationStatus.PROTECTED


def test_protection_persists_mapping_and_local_direction_restores(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, _repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    outgoing = decide_policy(
        ToolPolicy.SAFE_TOOL_CALLS,
        Direction.TO_PROVIDER,
        ContentKind.TOOL_ARGUMENT,
    )
    incoming = decide_policy(
        ToolPolicy.SAFE_TOOL_CALLS,
        Direction.TO_LOCAL,
        ContentKind.TOOL_ARGUMENT,
    )

    protected = lifecycle.process(CONVERSATION_ID, "Alice", person_span("Alice"), outgoing)
    assert protected.status is ConversationStatus.PROTECTED
    assert protected.text is not None and "Alice" not in protected.text

    restored = lifecycle.process(CONVERSATION_ID, protected.text, (), incoming)
    assert restored.status is ConversationStatus.PROTECTED
    assert restored.text == "Alice"


def test_known_processing_failure_blocks_without_text_or_activity_refresh(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    decision = decide_policy(ToolPolicy.DEFAULT, Direction.TO_LOCAL, ContentKind.CONVERSATION)
    clock.value += timedelta(days=1)

    blocked = lifecycle.process(CONVERSATION_ID, "<P999>", (), decision)

    assert blocked.status is ConversationStatus.BLOCKED
    assert blocked.text is None
    assert blocked.reason == "unknown-substitute"
    assert repository.load(CONVERSATION_ID).last_activity == datetime(2026, 1, 1, tzinfo=UTC)


def test_default_tool_passage_is_explicit_and_bypass_returns_raw_text(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, _repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    decision = decide_policy(ToolPolicy.DEFAULT, Direction.TO_PROVIDER, ContentKind.TOOL_RESULT)

    default_result = lifecycle.process(CONVERSATION_ID, "Alice", person_span("Alice"), decision)
    assert default_result.text == "Alice"
    assert default_result.warning_code == "tool-data-unprotected"

    lifecycle.accept_bypass(CONVERSATION_ID, warning_accepted=True)
    bypassed = lifecycle.process(CONVERSATION_ID, "PRIVATE", (), decision)
    assert bypassed.status is ConversationStatus.BYPASSED
    assert bypassed.text == "PRIVATE"
    assert bypassed.warning_code == "conversation-bypass-active"


def test_compatibility_policy_uses_surrogates_and_rejects_mode_switch(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, _repository = service(tmp_path, clock)
    lifecycle.create(
        fresh_state(CONVERSATION_ID, clock, mode=SubstitutionMode.COMPATIBILITY)
    )
    compatibility = decide_policy(
        ToolPolicy.TOOL_COMPATIBILITY,
        Direction.TO_PROVIDER,
        ContentKind.CONVERSATION,
    )
    compatible = lifecycle.process(
        CONVERSATION_ID,
        "Alice",
        person_span("Alice"),
        compatibility,
    )
    assert compatible.text == "Alex Morgan"

    alias_decision = decide_policy(
        ToolPolicy.SAFE_TOOL_CALLS,
        Direction.TO_PROVIDER,
        ContentKind.CONVERSATION,
    )
    blocked = lifecycle.process(CONVERSATION_ID, "Bob", person_span("Bob"), alias_decision)
    assert blocked.status is ConversationStatus.BLOCKED
    assert blocked.reason == "policy-mode-mismatch"


def test_cleanup_is_idempotent_and_preserves_active_conversations(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, _repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    clock.value += timedelta(days=20)
    lifecycle.create(fresh_state(OTHER_ID, clock))
    clock.value += timedelta(days=10)

    assert lifecycle.cleanup_expired() == 1
    assert lifecycle.cleanup_expired() == 0
    assert lifecycle.resume(CONVERSATION_ID).status is ConversationStatus.MISSING
    assert lifecycle.resume(OTHER_ID).status is ConversationStatus.PROTECTED


def test_cleanup_rechecks_activity_after_candidate_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    clock.value += RETENTION_PERIOD
    original_delete = repository.delete_if_inactive
    refreshed = False

    def refresh_then_delete(
        conversation_id: str | UUID,
        *,
        inactive_since: datetime,
    ) -> bool:
        nonlocal refreshed
        if not refreshed:
            refreshed = True
            current = repository.load(conversation_id)
            repository.save(
                current.next_revision(last_activity=clock.value),
                expected_revision=current.revision,
            )
        return original_delete(conversation_id, inactive_since=inactive_since)

    monkeypatch.setattr(repository, "delete_if_inactive", refresh_then_delete)

    assert lifecycle.cleanup_expired() == 0
    assert repository.load(CONVERSATION_ID).last_activity == clock.value


def test_persistence_failure_blocks_even_deliberate_pass_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=UTC))
    lifecycle, repository = service(tmp_path, clock)
    lifecycle.create(fresh_state(CONVERSATION_ID, clock))
    decision = decide_policy(
        ToolPolicy.DEFAULT,
        Direction.TO_PROVIDER,
        ContentKind.TOOL_RESULT,
    )

    def fail_save(_state: ConversationState, *, expected_revision: int) -> None:
        del expected_revision
        raise VaultError("vault-write-failed")

    monkeypatch.setattr(repository, "save", fail_save)
    result = lifecycle.process(CONVERSATION_ID, "PRIVATE_SENTINEL", (), decision)

    assert result.status is ConversationStatus.BLOCKED
    assert result.text is None
    assert result.reason == "vault-write-failed"
