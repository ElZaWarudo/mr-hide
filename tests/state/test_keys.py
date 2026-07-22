from __future__ import annotations

import base64
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mr_hide.state.keys import MasterKeyManager, derive_conversation_key
from mr_hide.state.models import VaultError
from tests.fixtures.keyrings import ApprovedKeyring, LookalikeKeyring, RecordingKeyring
from tests.state.helpers import CONVERSATION_ID, MASTER_KEY, OTHER_CONVERSATION_ID


class ConcurrentKeyring(ApprovedKeyring):
    def __init__(self) -> None:
        super().__init__()
        self.guard = threading.Lock()

    def get_password(self, service: str, account: str) -> str | None:
        with self.guard:
            time.sleep(0.01)
            return super().get_password(service, account)

    def set_password(self, service: str, account: str, password: str) -> None:
        with self.guard:
            super().set_password(service, account, password)


def manager(path: Path, backend: RecordingKeyring) -> MasterKeyManager:
    return MasterKeyManager(
        path,
        backend=backend,
        approved_types=(ApprovedKeyring, ConcurrentKeyring),
    )


def test_master_key_is_created_once_and_reloaded(tmp_path: Path) -> None:
    backend = ApprovedKeyring()
    keys = manager(tmp_path, backend)

    first = keys.get_or_create()
    second = keys.get_or_create()
    loaded = keys.load_existing()

    assert first == second == loaded
    assert len(first) == 32
    assert [call[0] for call in backend.calls].count("set") == 1
    assert first not in (tmp_path / ".master-key.lock").read_bytes()


def test_missing_existing_key_does_not_create_replacement(tmp_path: Path) -> None:
    backend = ApprovedKeyring()

    with pytest.raises(VaultError, match="master-key-missing"):
        manager(tmp_path, backend).load_existing()

    assert all(call[0] != "set" for call in backend.calls)


def test_unapproved_and_subclass_backends_fail_before_access(tmp_path: Path) -> None:
    for backend in (RecordingKeyring(), LookalikeKeyring()):
        with pytest.raises(VaultError, match="keyring-not-approved"):
            MasterKeyManager(
                tmp_path,
                backend=backend,
                approved_types=(ApprovedKeyring,),
            ).get_or_create()
        assert backend.calls == []


def test_invalid_stored_key_fails_without_overwrite(tmp_path: Path) -> None:
    backend = ApprovedKeyring(returned_value="not-valid-base64")

    with pytest.raises(VaultError, match="master-key-invalid"):
        manager(tmp_path, backend).get_or_create()

    assert all(call[0] != "set" for call in backend.calls)


@pytest.mark.parametrize("failure", ("get", "set"))
def test_keyring_failures_are_redacted(tmp_path: Path, failure: str) -> None:
    backend = ApprovedKeyring(fail_on=failure)

    with pytest.raises(VaultError) as caught:
        manager(tmp_path, backend).get_or_create()

    assert "sentinel" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_concurrent_initialization_returns_one_key(tmp_path: Path) -> None:
    backend = ConcurrentKeyring()

    def create() -> bytes:
        return manager(tmp_path, backend).get_or_create()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(executor.map(lambda _index: create(), range(4)))

    assert len(set(results)) == 1
    assert [call[0] for call in backend.calls].count("set") == 1


def test_conversation_keys_are_deterministic_and_separated() -> None:
    first = derive_conversation_key(MASTER_KEY, CONVERSATION_ID)

    assert first == derive_conversation_key(MASTER_KEY, CONVERSATION_ID)
    assert first != derive_conversation_key(MASTER_KEY, OTHER_CONVERSATION_ID)


def test_valid_preexisting_key_decodes_exactly(tmp_path: Path) -> None:
    encoded = base64.urlsafe_b64encode(MASTER_KEY).decode("ascii")
    backend = ApprovedKeyring(returned_value=encoded)

    assert manager(tmp_path, backend).load_existing() == MASTER_KEY
