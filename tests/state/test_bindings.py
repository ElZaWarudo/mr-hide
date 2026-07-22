from __future__ import annotations

import json
from pathlib import Path

import pytest

from mr_hide.state import BindingRegistry, VaultError
from tests.state.helpers import CONVERSATION_ID, OTHER_CONVERSATION_ID

NATIVE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_registry_stores_only_client_scoped_hash(tmp_path: Path) -> None:
    registry = BindingRegistry(tmp_path)
    registry.bind("codex", NATIVE_ID, CONVERSATION_ID)

    payload = (tmp_path / "bindings.json").read_text(encoding="utf-8")

    assert NATIVE_ID not in payload
    assert registry.lookup("codex", NATIVE_ID) == CONVERSATION_ID
    assert registry.lookup("claude", NATIVE_ID) is None


def test_binding_is_idempotent_but_cannot_be_reassigned(tmp_path: Path) -> None:
    registry = BindingRegistry(tmp_path)
    registry.bind("codex", NATIVE_ID, CONVERSATION_ID)
    registry.bind("codex", NATIVE_ID, CONVERSATION_ID)

    with pytest.raises(VaultError, match="native-binding-conflict"):
        registry.bind("codex", NATIVE_ID, OTHER_CONVERSATION_ID)


@pytest.mark.parametrize(
    "identity",
    ("", "../session", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA", "not-a-uuid"),
)
def test_native_identity_must_be_a_canonical_uuid(tmp_path: Path, identity: str) -> None:
    with pytest.raises(VaultError, match="invalid-native-identity"):
        BindingRegistry(tmp_path).lookup("codex", identity)


def test_duplicate_or_malformed_registry_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bindings.json"
    path.write_text(
        '{"schema_version":1,"schema_version":1,"records":{}}',
        encoding="utf-8",
    )

    with pytest.raises(VaultError, match="binding-registry-invalid"):
        BindingRegistry(tmp_path).lookup("codex", NATIVE_ID)

    path.write_text(json.dumps({"schema_version": 1, "records": {"bad": "value"}}))
    with pytest.raises(VaultError, match="binding-registry-invalid"):
        BindingRegistry(tmp_path).lookup("codex", NATIVE_ID)
