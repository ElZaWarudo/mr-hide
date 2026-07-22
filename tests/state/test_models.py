from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from mr_hide.privacy.mapping import MappingRecord, MappingTable, SubstitutionMode
from mr_hide.state.models import ConversationState, VaultError, parse_conversation_id
from tests.state.helpers import CONVERSATION_ID, sample_state


@pytest.mark.parametrize("revision", (True, "1", -1))
def test_state_rejects_invalid_revision_types(revision: object) -> None:
    state = sample_state()

    with pytest.raises(VaultError, match="invalid-state-revision"):
        replace(state, revision=revision)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    (
        "../vault",
        "{12345678-1234-5678-9234-567812345678}",
        "12345678123456789234567812345678",
        "12345678-1234-5678-9234-567812345678/other",
        "12345678-1234-5678-9234-56781234567Z",
    ),
)
def test_conversation_identifier_must_be_canonical_uuid(value: str) -> None:
    with pytest.raises(VaultError, match="invalid-conversation-id"):
        parse_conversation_id(value)


def test_conversation_identifier_accepts_canonical_string_and_uuid() -> None:
    assert parse_conversation_id(str(CONVERSATION_ID)) == CONVERSATION_ID
    assert parse_conversation_id(CONVERSATION_ID) == CONVERSATION_ID


def test_new_state_requires_aware_utc_time() -> None:
    with pytest.raises(VaultError, match="invalid-state-timestamp"):
        ConversationState.new(
            CONVERSATION_ID,
            mode=SubstitutionMode.ALIAS,
            now=datetime(2026, 7, 22),
        )


def test_next_revision_updates_activity_without_mutating_prior_state() -> None:
    state = sample_state()
    later = state.last_activity + timedelta(hours=1)

    updated = state.next_revision(last_activity=later, bypassed=True)

    assert state.revision == 0
    assert not state.bypassed
    assert updated.revision == 1
    assert updated.bypassed
    assert updated.last_activity == later


def test_state_rejects_mapping_mode_mismatch() -> None:
    state = sample_state()
    incompatible = MappingTable(
        (
            MappingRecord(
                "PERSON",
                "alice",
                "Alice",
                "Alex Morgan",
                SubstitutionMode.COMPATIBILITY,
            ),
        )
    )

    with pytest.raises(VaultError, match="invalid-state-policy"):
        ConversationState(
            conversation_id=state.conversation_id,
            revision=0,
            created_at=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            mode=SubstitutionMode.ALIAS,
            bypassed=False,
            mappings=incompatible,
        )


def test_state_rejects_activity_before_creation() -> None:
    now = datetime.now(UTC)

    with pytest.raises(VaultError, match="invalid-state-timestamp"):
        ConversationState(
            conversation_id=UUID(int=1),
            revision=0,
            created_at=now,
            last_activity=now - timedelta(seconds=1),
            mode=SubstitutionMode.ALIAS,
            bypassed=False,
            mappings=MappingTable(),
        )
