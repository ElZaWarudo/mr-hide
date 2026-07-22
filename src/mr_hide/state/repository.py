"""Revision-checked repository over key, codec, lock, and atomic-store ports."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mr_hide.state.codec import VaultCodec
from mr_hide.state.keys import MasterKeyProvider
from mr_hide.state.models import (
    ConversationState,
    VaultError,
    parse_conversation_id,
    require_utc,
)
from mr_hide.state.store import AtomicVaultStore


class VaultRepository:
    def __init__(
        self,
        store: AtomicVaultStore,
        key_provider: MasterKeyProvider,
        codec: VaultCodec | None = None,
    ) -> None:
        self._store = store
        self._keys = key_provider
        self._codec = codec or VaultCodec()

    def create(self, state: ConversationState) -> None:
        conversation_id = parse_conversation_id(state.conversation_id)
        if state.revision != 0:
            raise VaultError("invalid-initial-revision")
        with self._store.lock(conversation_id):
            if self._store.exists_unlocked(conversation_id):
                raise VaultError("vault-already-exists")
            master_key = self._keys.get_or_create()
            payload = self._codec.encrypt(state, master_key)
            self._store.write_unlocked(conversation_id, payload)

    def load(self, conversation_id: str | UUID) -> ConversationState:
        parsed = parse_conversation_id(conversation_id)
        with self._store.lock(parsed):
            return self._load_unlocked(parsed)

    def conversation_ids(self) -> tuple[UUID, ...]:
        return self._store.conversation_ids()

    def delete_if_inactive(
        self,
        conversation_id: str | UUID,
        *,
        inactive_since: datetime,
    ) -> bool:
        parsed = parse_conversation_id(conversation_id)
        cutoff = require_utc(inactive_since)
        with self._store.lock(parsed):
            if not self._store.exists_unlocked(parsed):
                return False
            current = self._load_unlocked(parsed)
            if current.last_activity > cutoff:
                return False
            return self._store.delete_unlocked(parsed)

    def save(self, state: ConversationState, *, expected_revision: int) -> None:
        conversation_id = parse_conversation_id(state.conversation_id)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise VaultError("invalid-expected-revision")
        if state.revision != expected_revision + 1:
            raise VaultError("invalid-next-revision")
        with self._store.lock(conversation_id):
            current = self._load_unlocked(conversation_id)
            if current.revision != expected_revision:
                raise VaultError("stale-vault-write")
            master_key = self._keys.load_existing()
            payload = self._codec.encrypt(state, master_key)
            self._store.write_unlocked(conversation_id, payload)

    def _load_unlocked(self, conversation_id: UUID) -> ConversationState:
        payload = self._store.read_unlocked(conversation_id)
        master_key = self._keys.load_existing()
        return self._codec.decrypt(payload, master_key, conversation_id)
