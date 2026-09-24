"""Crash-safe native-client identity to conversation bindings."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import UUID

import portalocker

from mr_hide.state.models import VaultError, parse_conversation_id

_SCHEMA_VERSION = 1
_MAX_REGISTRY_BYTES = 1024 * 1024
_LOCK_TIMEOUT_SECONDS = 30


class BindingRegistry:
    """Store only keyed hashes of canonical native session UUIDs."""

    def __init__(self, state_directory: Path) -> None:
        self._root = state_directory
        self._path = state_directory / "bindings.json"
        self._lock_path = state_directory / ".bindings.lock"
        self._prepare_root()

    def lookup(self, client: str, native_identity: str) -> UUID | None:
        key = _binding_key(client, native_identity)
        with self._lock():
            records = self._read_unlocked(allow_overflow=True)
            value = records.get(key)
        return None if value is None else parse_conversation_id(value)

    def bind(self, client: str, native_identity: str, conversation_id: str | UUID) -> None:
        key = _binding_key(client, native_identity)
        parsed = parse_conversation_id(conversation_id)
        with self._lock():
            records = self._read_unlocked()
            existing = records.get(key)
            if existing is not None and existing != str(parsed):
                raise VaultError("native-binding-conflict")
            if existing is None:
                records[key] = str(parsed)
                self._write_unlocked(records)

    def prune_missing(self, active_conversations: Callable[[], tuple[UUID, ...]]) -> int:
        with self._lock():
            active = {str(identifier) for identifier in active_conversations()}
            records = self._read_unlocked(allow_overflow=True)
            retained = {key: value for key, value in records.items() if value in active}
            if len(retained) != len(records):
                self._write_unlocked(retained)
            return len(records) - len(retained)

    def _read_unlocked(self, *, allow_overflow: bool = False) -> dict[str, str]:
        try:
            if not self._path.exists():
                return {}
            if self._path.stat().st_size > _MAX_REGISTRY_BYTES:
                raise VaultError("binding-registry-too-large")
            payload = self._path.read_bytes()
            document = json.loads(
                payload,
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
        except VaultError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            raise VaultError("binding-registry-invalid") from None
        if (
            not isinstance(document, dict)
            or set(document) != {"schema_version", "records"}
            or document["schema_version"] != _SCHEMA_VERSION
            or not isinstance(document["records"], dict)
        ):
            raise VaultError("binding-registry-invalid")
        records = document["records"]
        if len(records) > 10_000 and not allow_overflow:
            raise VaultError("binding-registry-invalid")
        for key, value in records.items():
            if (
                not isinstance(key, str)
                or len(key) != 64
                or any(character not in "0123456789abcdef" for character in key)
                or not isinstance(value, str)
            ):
                raise VaultError("binding-registry-invalid")
            parse_conversation_id(value)
        return records

    def _write_unlocked(self, records: dict[str, str]) -> None:
        payload = json.dumps(
            {"schema_version": _SCHEMA_VERSION, "records": records},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) > _MAX_REGISTRY_BYTES:
            raise VaultError("binding-registry-too-large")
        descriptor = -1
        temporary: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(
                dir=self._root,
                prefix=".bindings-write-",
                suffix=".tmp",
            )
            temporary = Path(raw_path)
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            temporary = None
        except VaultError:
            raise
        except OSError:
            raise VaultError("binding-registry-write-failed") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        try:
            with portalocker.Lock(
                str(self._lock_path),
                mode="a",
                timeout=_LOCK_TIMEOUT_SECONDS,
            ):
                yield
        except VaultError:
            raise
        except Exception:
            raise VaultError("binding-registry-lock-failed") from None

    def _prepare_root(self) -> None:
        try:
            self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt":
                self._root.chmod(0o700)
        except OSError:
            raise VaultError("binding-directory-unavailable") from None


def _binding_key(client: str, native_identity: str) -> str:
    if client not in {"codex", "claude"}:
        raise VaultError("invalid-binding-client")
    if not isinstance(native_identity, str) or len(native_identity) > 100:
        raise VaultError("invalid-native-identity")
    try:
        parsed = UUID(native_identity)
    except (ValueError, TypeError, AttributeError):
        raise VaultError("invalid-native-identity") from None
    if native_identity != str(parsed):
        raise VaultError("invalid-native-identity")
    material = client.encode("ascii") + b"\0" + native_identity.encode("ascii")
    return hashlib.sha256(material).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VaultError("binding-registry-invalid")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> object:
    raise VaultError("binding-registry-invalid")
