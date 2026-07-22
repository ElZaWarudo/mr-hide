from __future__ import annotations

import base64
import json

import pytest

from mr_hide.state.codec import VaultCodec
from mr_hide.state.models import VaultError
from tests.state.helpers import (
    CONVERSATION_ID,
    MASTER_KEY,
    ORIGINAL_SENTINEL,
    OTHER_CONVERSATION_ID,
    OTHER_MASTER_KEY,
    sample_state,
)


def test_encrypted_state_round_trips_without_plaintext() -> None:
    codec = VaultCodec()
    state = sample_state()

    payload = codec.encrypt(state, MASTER_KEY)
    restored = codec.decrypt(payload, MASTER_KEY, CONVERSATION_ID)

    assert restored == state
    assert ORIGINAL_SENTINEL.encode() not in payload
    assert MASTER_KEY not in payload


def test_fresh_nonce_changes_ciphertext_for_same_state() -> None:
    codec = VaultCodec()

    first = codec.encrypt(sample_state(), MASTER_KEY)
    second = codec.encrypt(sample_state(), MASTER_KEY)

    assert first != second


@pytest.mark.parametrize(
    ("key", "conversation_id", "reason"),
    (
        (OTHER_MASTER_KEY, CONVERSATION_ID, "vault-authentication-failed"),
        (MASTER_KEY, OTHER_CONVERSATION_ID, "vault-identity-mismatch"),
    ),
)
def test_wrong_key_or_identity_fails_closed(
    key: bytes,
    conversation_id: object,
    reason: str,
) -> None:
    payload = VaultCodec().encrypt(sample_state(), MASTER_KEY)

    with pytest.raises(VaultError, match=reason):
        VaultCodec().decrypt(payload, key, conversation_id)  # type: ignore[arg-type]


def test_tampered_ciphertext_fails_authentication() -> None:
    document = json.loads(VaultCodec().encrypt(sample_state(), MASTER_KEY))
    ciphertext = bytearray(base64.urlsafe_b64decode(document["ciphertext"]))
    ciphertext[-1] ^= 1
    document["ciphertext"] = base64.urlsafe_b64encode(ciphertext).decode("ascii")
    tampered = json.dumps(document).encode()

    with pytest.raises(VaultError, match="vault-authentication-failed"):
        VaultCodec().decrypt(tampered, MASTER_KEY, CONVERSATION_ID)


@pytest.mark.parametrize(
    ("payload", "reason"),
    (
        (b"not-json", "vault-envelope-invalid"),
        (b'{"schema_version":1}', "vault-envelope-invalid"),
        (
            b'{"schema_version":1,"schema_version":1,"conversation_id":"x",'
            b'"nonce":"x","ciphertext":"x"}',
            "vault-document-duplicate-key",
        ),
    ),
)
def test_malformed_envelopes_fail_with_safe_reason(payload: bytes, reason: str) -> None:
    with pytest.raises(VaultError, match=reason) as caught:
        VaultCodec().decrypt(payload, MASTER_KEY, CONVERSATION_ID)

    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "nonce_factory",
    (
        lambda _length: b"short",
        lambda _length: "not-bytes",
        lambda _length: (_ for _ in ()).throw(OSError("PRIVATE_SENTINEL")),
    ),
)
def test_invalid_nonce_factory_is_rejected(nonce_factory: object) -> None:
    codec = VaultCodec(nonce_factory)  # type: ignore[arg-type]

    with pytest.raises(VaultError, match="nonce-generation-failed") as caught:
        codec.encrypt(sample_state(), MASTER_KEY)

    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None
