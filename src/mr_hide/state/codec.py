"""Versioned AES-GCM envelope for conversation state."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from mr_hide.privacy.mapping import MappingRecord, MappingTable, SubstitutionMode
from mr_hide.state.keys import derive_conversation_key
from mr_hide.state.models import SCHEMA_VERSION, ConversationState, VaultError

_NONCE_BYTES = 12
_MAX_ENVELOPE_BYTES = 32 * 1024 * 1024
_OUTER_KEYS = {"schema_version", "conversation_id", "nonce", "ciphertext"}
_STATE_KEYS = {
    "schema_version",
    "conversation_id",
    "revision",
    "created_at",
    "last_activity",
    "mode",
    "bypassed",
    "mappings",
}
_MAPPING_KEYS = {"entity_type", "normalized", "original", "substitute", "mode"}


class VaultCodec:
    def __init__(self, nonce_factory: Callable[[int], bytes] = os.urandom) -> None:
        self._nonce_factory = nonce_factory

    def encrypt(self, state: ConversationState, master_key: bytes) -> bytes:
        key = derive_conversation_key(master_key, state.conversation_id)
        try:
            nonce = self._nonce_factory(_NONCE_BYTES)
        except Exception:
            raise VaultError("nonce-generation-failed") from None
        if not isinstance(nonce, bytes) or len(nonce) != _NONCE_BYTES:
            raise VaultError("nonce-generation-failed")
        plaintext = _canonical_json(_state_document(state))
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, _aad(state.conversation_id))
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "conversation_id": str(state.conversation_id),
            "nonce": _encode(nonce),
            "ciphertext": _encode(ciphertext),
        }
        return _canonical_json(envelope)

    def decrypt(
        self,
        payload: bytes,
        master_key: bytes,
        expected_conversation_id: UUID,
    ) -> ConversationState:
        if len(payload) > _MAX_ENVELOPE_BYTES:
            raise VaultError("vault-too-large")
        envelope = _load_object(payload, _OUTER_KEYS, "vault-envelope-invalid")
        if envelope.get("schema_version") != SCHEMA_VERSION:
            raise VaultError("unsupported-state-schema")
        if envelope.get("conversation_id") != str(expected_conversation_id):
            raise VaultError("vault-identity-mismatch")
        nonce = _decode_field(envelope.get("nonce"), "vault-envelope-invalid")
        ciphertext = _decode_field(envelope.get("ciphertext"), "vault-envelope-invalid")
        if len(nonce) != _NONCE_BYTES:
            raise VaultError("vault-envelope-invalid")
        key = derive_conversation_key(master_key, expected_conversation_id)
        try:
            plaintext = AESGCM(key).decrypt(
                nonce,
                ciphertext,
                _aad(expected_conversation_id),
            )
        except (InvalidTag, ValueError):
            raise VaultError("vault-authentication-failed") from None
        state_document = _load_object(plaintext, _STATE_KEYS, "vault-state-invalid")
        return _parse_state(state_document, expected_conversation_id)


def _aad(conversation_id: UUID) -> bytes:
    return f"mr-hide:v{SCHEMA_VERSION}:{conversation_id}".encode("ascii")


def _canonical_json(document: object) -> bytes:
    try:
        return json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise VaultError("vault-state-invalid") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VaultError("vault-document-duplicate-key")
        result[key] = value
    return result


def _load_object(payload: bytes, keys: set[str], reason: str) -> dict[str, Any]:
    try:
        document: object = json.loads(payload, object_pairs_hook=_unique_object)
    except VaultError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise VaultError(reason) from None
    if not isinstance(document, dict) or set(document) != keys:
        raise VaultError(reason)
    return document


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _decode_field(value: object, reason: str) -> bytes:
    if not isinstance(value, str):
        raise VaultError(reason)
    try:
        return base64.b64decode(value, altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise VaultError(reason) from None


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _state_document(state: ConversationState) -> dict[str, object]:
    return {
        "schema_version": state.schema_version,
        "conversation_id": str(state.conversation_id),
        "revision": state.revision,
        "created_at": _timestamp(state.created_at),
        "last_activity": _timestamp(state.last_activity),
        "mode": state.mode.value,
        "bypassed": state.bypassed,
        "mappings": [
            {
                "entity_type": item.entity_type,
                "normalized": item.normalized,
                "original": item.original,
                "substitute": item.substitute,
                "mode": item.mode.value,
            }
            for item in state.mappings.records
        ],
    }


def _parse_state(document: dict[str, Any], expected_id: UUID) -> ConversationState:
    if document.get("conversation_id") != str(expected_id):
        raise VaultError("vault-identity-mismatch")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise VaultError("unsupported-state-schema")
    try:
        raw_mappings = document["mappings"]
        if not isinstance(raw_mappings, list):
            raise ValueError
        mappings = MappingTable(tuple(_parse_mapping(item) for item in raw_mappings))
        return ConversationState(
            conversation_id=expected_id,
            revision=_required_int(document["revision"]),
            created_at=_required_timestamp(document["created_at"]),
            last_activity=_required_timestamp(document["last_activity"]),
            mode=SubstitutionMode(document["mode"]),
            bypassed=_required_bool(document["bypassed"]),
            mappings=mappings,
        )
    except VaultError:
        raise
    except Exception:
        raise VaultError("vault-state-invalid") from None


def _parse_mapping(value: object) -> MappingRecord:
    if not isinstance(value, dict) or set(value) != _MAPPING_KEYS:
        raise VaultError("vault-state-invalid")
    try:
        fields = {key: value[key] for key in _MAPPING_KEYS}
        if not all(isinstance(fields[key], str) for key in _MAPPING_KEYS):
            raise ValueError
        return MappingRecord(
            entity_type=fields["entity_type"],
            normalized=fields["normalized"],
            original=fields["original"],
            substitute=fields["substitute"],
            mode=SubstitutionMode(fields["mode"]),
        )
    except (KeyError, ValueError):
        raise VaultError("vault-state-invalid") from None


def _required_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VaultError("vault-state-invalid")
    return value


def _required_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise VaultError("vault-state-invalid")
    return value


def _required_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise VaultError("vault-state-invalid")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise VaultError("vault-state-invalid") from None
