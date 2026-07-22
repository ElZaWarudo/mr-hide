"""Validated, protocol-neutral conversation state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from mr_hide.privacy.mapping import MappingTable, SubstitutionMode

SCHEMA_VERSION = 1


class VaultError(RuntimeError):
    """A safe state-layer failure containing only a stable reason code."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def parse_conversation_id(value: str | UUID) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise VaultError("invalid-conversation-id") from None
    if value != str(parsed):
        raise VaultError("invalid-conversation-id")
    return parsed


def require_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise VaultError("invalid-state-timestamp")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ConversationState:
    conversation_id: UUID
    revision: int
    created_at: datetime
    last_activity: datetime
    mode: SubstitutionMode
    bypassed: bool
    mappings: MappingTable
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise VaultError("unsupported-state-schema")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
        ):
            raise VaultError("invalid-state-revision")
        conversation_id = parse_conversation_id(self.conversation_id)
        created = require_utc(self.created_at)
        activity = require_utc(self.last_activity)
        if activity < created:
            raise VaultError("invalid-state-timestamp")
        if (
            not isinstance(self.mode, SubstitutionMode)
            or not isinstance(self.bypassed, bool)
            or not isinstance(self.mappings, MappingTable)
        ):
            raise VaultError("invalid-state-policy")
        if self.mappings.records and any(
            record.mode is not self.mode for record in self.mappings.records
        ):
            raise VaultError("invalid-state-policy")
        object.__setattr__(self, "conversation_id", conversation_id)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "last_activity", activity)

    @classmethod
    def new(
        cls,
        conversation_id: str | UUID,
        *,
        mode: SubstitutionMode,
        now: datetime,
    ) -> ConversationState:
        timestamp = require_utc(now)
        return cls(
            conversation_id=parse_conversation_id(conversation_id),
            revision=0,
            created_at=timestamp,
            last_activity=timestamp,
            mode=mode,
            bypassed=False,
            mappings=MappingTable(),
        )

    def next_revision(
        self,
        *,
        mappings: MappingTable | None = None,
        bypassed: bool | None = None,
        last_activity: datetime | None = None,
    ) -> ConversationState:
        return replace(
            self,
            revision=self.revision + 1,
            mappings=self.mappings if mappings is None else mappings,
            bypassed=self.bypassed if bypassed is None else bypassed,
            last_activity=(
                self.last_activity if last_activity is None else require_utc(last_activity)
            ),
        )
