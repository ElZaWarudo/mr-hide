from __future__ import annotations

import pytest

from mr_hide.security.keyring_probe import probe_keyring


@pytest.mark.system_keyring
def test_platform_keyring_provides_approved_round_trip() -> None:
    result = probe_keyring()

    assert result.supported, f"{result.backend}: {result.reason}"
