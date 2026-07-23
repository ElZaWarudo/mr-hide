from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest

from mr_hide.state.models import VaultError
from mr_hide.state.store import AtomicVaultStore

CONVERSATION_ID = UUID("12345678-1234-5678-9234-567812345678")


def test_atomic_store_round_trips_and_replaces_ciphertext(tmp_path: Path) -> None:
    store = AtomicVaultStore(tmp_path / "state")

    with store.lock(CONVERSATION_ID):
        store.write_unlocked(CONVERSATION_ID, b"first")
        assert store.read_unlocked(CONVERSATION_ID) == b"first"
        store.write_unlocked(CONVERSATION_ID, b"second")
        assert store.read_unlocked(CONVERSATION_ID) == b"second"

    assert not tuple(store.root.glob(".vault-write-*.tmp"))


def test_failed_replace_preserves_previous_vault_and_removes_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AtomicVaultStore(tmp_path / "state")
    with store.lock(CONVERSATION_ID):
        store.write_unlocked(CONVERSATION_ID, b"previous")

        def fail_replace(_source: object, _target: object) -> None:
            raise OSError("PRIVATE_SENTINEL")

        monkeypatch.setattr("mr_hide.state.store.os.replace", fail_replace)
        with pytest.raises(VaultError, match="vault-write-failed") as caught:
            store.write_unlocked(CONVERSATION_ID, b"new")

        assert store.read_unlocked(CONVERSATION_ID) == b"previous"
        assert "PRIVATE_SENTINEL" not in str(caught.value)
        assert not tuple(store.root.glob(".vault-write-*.tmp"))


def test_missing_and_invalid_writes_use_safe_errors(tmp_path: Path) -> None:
    store = AtomicVaultStore(tmp_path / "state")

    with store.lock(CONVERSATION_ID):
        with pytest.raises(VaultError, match="vault-missing"):
            store.read_unlocked(CONVERSATION_ID)
        with pytest.raises(VaultError, match="vault-write-invalid"):
            store.write_unlocked(CONVERSATION_ID, b"")


def test_store_lists_canonical_vaults_and_deletes_idempotently(tmp_path: Path) -> None:
    store = AtomicVaultStore(tmp_path / "state")
    with store.lock(CONVERSATION_ID):
        store.write_unlocked(CONVERSATION_ID, b"ciphertext")
    (store.root / "not-a-uuid.vault").write_bytes(b"ignored")

    assert store.conversation_ids() == (CONVERSATION_ID,)
    with store.lock(CONVERSATION_ID):
        assert store.delete_unlocked(CONVERSATION_ID)
        assert not store.delete_unlocked(CONVERSATION_ID)


def test_store_bounds_vault_enumeration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AtomicVaultStore(tmp_path / "state")
    original_glob = Path.glob
    candidates = tuple(store.root / f"{UUID(int=index)}.vault" for index in range(10_001))

    def bounded_fixture(path: Path, pattern: str) -> Iterator[Path]:
        if path == store.root and pattern == "*.vault":
            return iter(candidates)
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", bounded_fixture)

    with pytest.raises(VaultError, match="vault-list-too-large"):
        store.conversation_ids()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission assertion")
def test_state_directory_and_vault_are_owner_only(tmp_path: Path) -> None:
    store = AtomicVaultStore(tmp_path / "state")
    with store.lock(CONVERSATION_ID):
        store.write_unlocked(CONVERSATION_ID, b"ciphertext")

    assert store.root.stat().st_mode & 0o777 == 0o700
    assert (store.root / f"{CONVERSATION_ID}.vault").stat().st_mode & 0o777 == 0o600
