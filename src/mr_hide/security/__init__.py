"""Fail-closed capability checks for future privacy storage."""

from mr_hide.security.keyring_probe import (
    KeyringCapability,
    approved_backend_types,
    backend_name,
    probe_keyring,
)

__all__ = [
    "KeyringCapability",
    "approved_backend_types",
    "backend_name",
    "probe_keyring",
]
