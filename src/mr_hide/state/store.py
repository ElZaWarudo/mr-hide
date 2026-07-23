"""Cross-platform locked and crash-safe ciphertext storage."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from itertools import islice
from pathlib import Path
from uuid import UUID

import portalocker

from mr_hide.state.models import VaultError

_MAX_VAULT_BYTES = 32 * 1024 * 1024
_MAX_VAULT_FILES = 10_000
_LOCK_TIMEOUT_SECONDS = 30


class AtomicVaultStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._prepare_root()

    @contextmanager
    def lock(self, conversation_id: UUID) -> Iterator[None]:
        path = self.root / f"{conversation_id}.lock"
        try:
            with portalocker.Lock(
                str(path),
                mode="a",
                timeout=_LOCK_TIMEOUT_SECONDS,
            ):
                yield
        except VaultError:
            raise
        except Exception:
            raise VaultError("vault-lock-failed") from None

    def exists_unlocked(self, conversation_id: UUID) -> bool:
        return self._path(conversation_id).is_file()

    def conversation_ids(self) -> tuple[UUID, ...]:
        identifiers: list[UUID] = []
        try:
            paths = tuple(islice(self.root.glob("*.vault"), _MAX_VAULT_FILES + 1))
        except OSError:
            raise VaultError("vault-list-failed") from None
        if len(paths) > _MAX_VAULT_FILES:
            raise VaultError("vault-list-too-large")
        for path in paths:
            try:
                identifier = UUID(path.stem)
            except ValueError:
                continue
            if path.stem == str(identifier) and path.is_file():
                identifiers.append(identifier)
        return tuple(sorted(identifiers, key=str))

    def read_unlocked(self, conversation_id: UUID) -> bytes:
        path = self._path(conversation_id)
        try:
            size = path.stat().st_size
            if size > _MAX_VAULT_BYTES:
                raise VaultError("vault-too-large")
            return path.read_bytes()
        except VaultError:
            raise
        except FileNotFoundError:
            raise VaultError("vault-missing") from None
        except OSError:
            raise VaultError("vault-read-failed") from None

    def write_unlocked(self, conversation_id: UUID, payload: bytes) -> None:
        if not payload or len(payload) > _MAX_VAULT_BYTES:
            raise VaultError("vault-write-invalid")
        target = self._path(conversation_id)
        descriptor = -1
        temporary_path: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(
                dir=self.root,
                prefix=".vault-write-",
                suffix=".tmp",
            )
            temporary_path = Path(raw_path)
            if os.name != "nt":
                os.chmod(temporary_path, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, target)
            temporary_path = None
            self._sync_directory()
        except VaultError:
            raise
        except OSError:
            raise VaultError("vault-write-failed") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

    def delete_unlocked(self, conversation_id: UUID) -> bool:
        try:
            self._path(conversation_id).unlink()
            self._sync_directory()
        except FileNotFoundError:
            return False
        except OSError:
            raise VaultError("vault-delete-failed") from None
        return True

    def _path(self, conversation_id: UUID) -> Path:
        return self.root / f"{conversation_id}.vault"

    def _prepare_root(self) -> None:
        try:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt":
                self.root.chmod(0o700)
        except OSError:
            raise VaultError("vault-directory-unavailable") from None

    def _sync_directory(self) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
