"""Qualify an exact OS-backed keyring with a synthetic round trip."""

from __future__ import annotations

import hmac
import secrets
import sys
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

import keyring


class KeyringBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...

    def get_password(self, service: str, username: str) -> str | None: ...

    def delete_password(self, service: str, username: str) -> None: ...


@dataclass(frozen=True, slots=True)
class KeyringCapability:
    supported: bool
    backend: str
    reason: str


def _platform_backend_types() -> tuple[type[object], ...]:
    try:
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring

            return (WinVaultKeyring,)
        if sys.platform.startswith("linux"):
            from keyring.backends.SecretService import Keyring

            return (Keyring,)
    except ImportError:
        return ()
    return ()


def _backend_name(backend: object) -> str:
    backend_type = type(backend)
    return f"{backend_type.__module__}.{backend_type.__qualname__}"


def approved_backend_types() -> tuple[type[object], ...]:
    """Return the exact OS-backed keyring types approved for this platform."""

    return _platform_backend_types()


def backend_name(backend: object) -> str:
    """Return a non-secret backend type name suitable for diagnostics."""

    return _backend_name(backend)


def probe_keyring(
    *,
    backend: KeyringBackend | None = None,
    approved_backend_types: tuple[type[object], ...] | None = None,
) -> KeyringCapability:
    """Return a redacted capability result and never fall back to another backend."""

    try:
        active = backend if backend is not None else keyring.get_keyring()
    except Exception:
        return KeyringCapability(False, "unavailable", "probe-failed")
    backend_name = _backend_name(active)
    try:
        approved = (
            _platform_backend_types()
            if approved_backend_types is None
            else approved_backend_types
        )
    except Exception:
        return KeyringCapability(False, backend_name, "probe-failed")
    if type(active) not in approved:
        return KeyringCapability(False, backend_name, "backend-not-approved")

    nonce = uuid4().hex
    service = f"mr-hide-capability-{nonce}"
    account = f"probe-{nonce}"
    sentinel = secrets.token_urlsafe(32)
    supported = False
    reason = "probe-failed"
    cleanup_failed = False
    try:
        active.set_password(service, account, sentinel)
        returned = active.get_password(service, account)
        if returned is None or not hmac.compare_digest(returned, sentinel):
            reason = "round-trip-mismatch"
        else:
            supported = True
            reason = "available"
    except Exception:
        supported = False
        reason = "probe-failed"
    finally:
        try:
            active.delete_password(service, account)
        except Exception:
            cleanup_failed = True

    if cleanup_failed:
        return KeyringCapability(False, backend_name, "probe-failed")
    return KeyringCapability(supported, backend_name, reason)
