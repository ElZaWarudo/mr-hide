from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import keyring
import pytest

from mr_hide.security.keyring_probe import probe_keyring
from mr_hide.state.keys import MasterKeyManager


@pytest.mark.system_keyring
def test_platform_keyring_provides_approved_round_trip() -> None:
    result = probe_keyring()

    assert result.supported, f"{result.backend}: {result.reason}"


@pytest.mark.system_keyring
def test_platform_keyring_holds_vault_master_key_separately(tmp_path: Path) -> None:
    backend = keyring.get_keyring()
    nonce = uuid4().hex
    service = f"mr-hide-system-test-{nonce}"
    account = f"master-{nonce}"
    manager = MasterKeyManager(
        tmp_path,
        backend=backend,
        service=service,
        account=account,
    )
    try:
        created = manager.get_or_create()

        assert len(created) == 32
        assert manager.load_existing() == created
        assert created not in b"".join(
            path.read_bytes() for path in tmp_path.iterdir() if path.is_file()
        )
    finally:
        with suppress(Exception):
            backend.delete_password(service, account)
