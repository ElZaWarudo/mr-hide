from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from mr_hide.privacy.mapping import (
    MappingRecord,
    MappingTable,
    SubstitutionMode,
)
from mr_hide.state.models import ConversationState

CONVERSATION_ID = UUID("12345678-1234-5678-9234-567812345678")
OTHER_CONVERSATION_ID = UUID("87654321-4321-6789-a234-567812345678")
MASTER_KEY = bytes(range(32))
OTHER_MASTER_KEY = bytes(reversed(range(32)))
ORIGINAL_SENTINEL = "PRIVATE_ORIGINAL_SENTINEL"


def sample_state(*, revision: int = 0) -> ConversationState:
    timestamp = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)
    return ConversationState(
        conversation_id=CONVERSATION_ID,
        revision=revision,
        created_at=timestamp,
        last_activity=timestamp,
        mode=SubstitutionMode.ALIAS,
        bypassed=False,
        mappings=MappingTable(
            (
                MappingRecord(
                    "PERSON",
                    ORIGINAL_SENTINEL.casefold(),
                    ORIGINAL_SENTINEL,
                    "<P0>",
                    SubstitutionMode.ALIAS,
                ),
            )
        ),
    )


class StaticKeyProvider:
    def __init__(self, key: bytes = MASTER_KEY) -> None:
        self.key = key
        self.created = 0
        self.loaded = 0

    def load_existing(self) -> bytes:
        self.loaded += 1
        return self.key

    def get_or_create(self) -> bytes:
        self.created += 1
        return self.key
