"""Approved-keyring master key lifecycle and per-conversation derivation."""

from __future__ import annotations

import base64
import hmac
import os
from pathlib import Path
from typing import Protocol
from uuid import UUID

import keyring
import portalocker
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from mr_hide.security import approved_backend_types
from mr_hide.state.models import VaultError

_SERVICE = "mr-hide-vault-v1"
_ACCOUNT = "installation-master-key"
_MASTER_KEY_BYTES = 32
_LOCK_TIMEOUT_SECONDS = 30


class KeyringBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...

    def get_password(self, service: str, username: str) -> str | None: ...


class MasterKeyProvider(Protocol):
    def load_existing(self) -> bytes: ...

    def get_or_create(self) -> bytes: ...


class MasterKeyManager:
    def __init__(
        self,
        state_directory: Path,
        *,
        backend: KeyringBackend | None = None,
        approved_types: tuple[type[object], ...] | None = None,
        service: str = _SERVICE,
        account: str = _ACCOUNT,
    ) -> None:
        if not service or not account or len(service) > 200 or len(account) > 200:
            raise VaultError("keyring-identity-invalid")
        self._state_directory = state_directory
        self._backend = backend
        self._approved_types = approved_types
        self._service = service
        self._account = account

    def load_existing(self) -> bytes:
        backend = self._approved_backend()
        encoded = self._read(backend)
        if encoded is None:
            raise VaultError("master-key-missing")
        return _decode_master_key(encoded)

    def get_or_create(self) -> bytes:
        self._prepare_directory()
        lock_path = self._state_directory / ".master-key.lock"
        try:
            with portalocker.Lock(
                str(lock_path),
                mode="a",
                timeout=_LOCK_TIMEOUT_SECONDS,
            ):
                backend = self._approved_backend()
                encoded = self._read(backend)
                if encoded is not None:
                    return _decode_master_key(encoded)
                try:
                    generated = os.urandom(_MASTER_KEY_BYTES)
                except Exception:
                    raise VaultError("master-key-generation-failed") from None
                serialized = base64.urlsafe_b64encode(generated).decode("ascii")
                try:
                    backend.set_password(self._service, self._account, serialized)
                except Exception:
                    raise VaultError("master-key-write-failed") from None
                confirmed = self._read(backend)
                if confirmed is None or not hmac.compare_digest(confirmed, serialized):
                    raise VaultError("master-key-write-failed")
                return generated
        except VaultError:
            raise
        except Exception:
            raise VaultError("master-key-lock-failed") from None

    def _approved_backend(self) -> KeyringBackend:
        try:
            backend = self._backend if self._backend is not None else keyring.get_keyring()
            approved = (
                approved_backend_types()
                if self._approved_types is None
                else self._approved_types
            )
        except Exception:
            raise VaultError("keyring-unavailable") from None
        if type(backend) not in approved:
            raise VaultError("keyring-not-approved")
        return backend

    def _read(self, backend: KeyringBackend) -> str | None:
        try:
            return backend.get_password(self._service, self._account)
        except Exception:
            raise VaultError("master-key-read-failed") from None

    def _prepare_directory(self) -> None:
        try:
            self._state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt":
                self._state_directory.chmod(0o700)
        except OSError:
            raise VaultError("vault-directory-unavailable") from None


def _decode_master_key(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise VaultError("master-key-invalid") from None
    if len(decoded) != _MASTER_KEY_BYTES:
        raise VaultError("master-key-invalid")
    return decoded


def derive_conversation_key(master_key: bytes, conversation_id: UUID) -> bytes:
    if len(master_key) != _MASTER_KEY_BYTES:
        raise VaultError("master-key-invalid")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=conversation_id.bytes,
        info=b"mr-hide-conversation-vault-v1",
    ).derive(master_key)
