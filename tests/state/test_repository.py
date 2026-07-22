from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest

from mr_hide.state.codec import VaultCodec
from mr_hide.state.models import VaultError
from mr_hide.state.repository import VaultRepository
from mr_hide.state.store import AtomicVaultStore
from tests.state.helpers import (
    CONVERSATION_ID,
    ORIGINAL_SENTINEL,
    StaticKeyProvider,
    sample_state,
)


def repository(path: Path, keys: StaticKeyProvider | None = None) -> VaultRepository:
    return VaultRepository(AtomicVaultStore(path), keys or StaticKeyProvider(), VaultCodec())


def test_repository_create_reload_and_restart(tmp_path: Path) -> None:
    keys = StaticKeyProvider()
    first = repository(tmp_path, keys)
    state = sample_state()

    first.create(state)
    restored = repository(tmp_path, keys).load(CONVERSATION_ID)

    assert restored == state
    payload = (tmp_path / f"{CONVERSATION_ID}.vault").read_bytes()
    assert ORIGINAL_SENTINEL.encode() not in payload


def test_duplicate_create_and_missing_load_fail_closed(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.create(sample_state())

    with pytest.raises(VaultError, match="vault-already-exists"):
        repo.create(sample_state())
    with pytest.raises(VaultError, match="vault-missing"):
        repository(tmp_path / "other").load(CONVERSATION_ID)


def test_revision_checked_save_rejects_stale_writer(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    initial = sample_state()
    repo.create(initial)
    first_update = initial.next_revision(bypassed=True)
    stale_update = initial.next_revision()

    repo.save(first_update, expected_revision=0)
    with pytest.raises(VaultError, match="stale-vault-write"):
        repo.save(stale_update, expected_revision=0)

    assert repo.load(CONVERSATION_ID) == first_update


def test_concurrent_writers_allow_exactly_one_revision(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    initial = sample_state()
    repo.create(initial)

    def save(bypassed: bool) -> str:
        try:
            repo.save(initial.next_revision(bypassed=bypassed), expected_revision=0)
        except VaultError as error:
            return error.reason
        return "saved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(save, (True, False)))

    assert sorted(results) == ["saved", "stale-vault-write"]
    assert repo.load(CONVERSATION_ID).revision == 1


def test_save_requires_exact_next_revision(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    state = sample_state()
    repo.create(state)

    with pytest.raises(VaultError, match="invalid-next-revision"):
        repo.save(state, expected_revision=0)


def test_rotated_or_missing_key_never_recreates_state(tmp_path: Path) -> None:
    keys = StaticKeyProvider()
    repo = repository(tmp_path, keys)
    repo.create(sample_state())
    keys.key = bytes(reversed(keys.key))

    with pytest.raises(VaultError, match="vault-authentication-failed"):
        repo.load(CONVERSATION_ID)

    assert keys.created == 1


def test_delete_rejects_naive_cutoff(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.create(sample_state())

    with pytest.raises(VaultError, match="invalid-state-timestamp"):
        repo.delete_if_inactive(CONVERSATION_ID, inactive_since=datetime(2026, 1, 1))

    assert repo.load(CONVERSATION_ID) == sample_state()
