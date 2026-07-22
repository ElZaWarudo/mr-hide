"""Authenticated encrypted conversation-state persistence."""

from mr_hide.state.codec import VaultCodec
from mr_hide.state.keys import MasterKeyManager
from mr_hide.state.lifecycle import (
    RETENTION_PERIOD,
    ConversationResult,
    ConversationService,
    ConversationStatus,
)
from mr_hide.state.models import ConversationState, VaultError, parse_conversation_id
from mr_hide.state.repository import VaultRepository
from mr_hide.state.store import AtomicVaultStore

__all__ = [
    "RETENTION_PERIOD",
    "AtomicVaultStore",
    "ConversationResult",
    "ConversationService",
    "ConversationState",
    "ConversationStatus",
    "MasterKeyManager",
    "VaultCodec",
    "VaultError",
    "VaultRepository",
    "parse_conversation_id",
]
