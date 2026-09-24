from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.models import DetectedSpan
from mr_hide.protocols.messages import MessagesRuntime
from mr_hide.protocols.responses import ResponsesRuntime
from mr_hide.runtime.privacy import PrivacyRuntime, PrivacyRuntimeError
from mr_hide.state import AtomicVaultStore, BindingRegistry, VaultRepository
from mr_hide.state.models import ConversationState, SubstitutionMode, VaultError
from tests.state.helpers import StaticKeyProvider

NOW = datetime(2026, 7, 22, 12, tzinfo=UTC)
STALE_ID = UUID("11111111-1111-4111-8111-111111111111")
ACTIVE_ID = UUID("22222222-2222-4222-8222-222222222222")
NEW_ID = UUID("33333333-3333-4333-8333-333333333333")
NATIVE_ID = UUID("44444444-4444-4444-8444-444444444444")


class NoopDetector:
    def detect(self, _text: str, **_kwargs: object) -> tuple[DetectedSpan, ...]:
        return ()


def repository(tmp_path: Path) -> VaultRepository:
    return VaultRepository(AtomicVaultStore(tmp_path / "vaults"), StaticKeyProvider())


@pytest.mark.parametrize("runtime_type", (ResponsesRuntime, MessagesRuntime))
def test_prepare_cleans_unrelated_expired_vaults_for_both_providers(
    tmp_path: Path,
    runtime_type: type[PrivacyRuntime],
) -> None:
    vaults = repository(tmp_path)
    vaults.create(
        ConversationState.new(
            STALE_ID,
            mode=SubstitutionMode.ALIAS,
            now=NOW - timedelta(days=30),
        )
    )
    vaults.create(
        ConversationState.new(
            ACTIVE_ID,
            mode=SubstitutionMode.ALIAS,
            now=NOW - timedelta(days=29),
        )
    )
    kwargs: dict[str, object] = {}
    if runtime_type is MessagesRuntime:
        kwargs["native_identifier_factory"] = lambda: NATIVE_ID

    runtime_type.prepare(
        repository=vaults,
        registry=BindingRegistry(tmp_path),
        detector=NoopDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=None,
        clock=lambda: NOW,
        identifier_factory=lambda: NEW_ID,
        **kwargs,
    )

    with pytest.raises(VaultError, match="vault-missing"):
        vaults.load(STALE_ID)
    assert vaults.load(ACTIVE_ID).conversation_id == ACTIVE_ID
    assert vaults.load(NEW_ID).conversation_id == NEW_ID


def test_cleanup_failure_blocks_before_new_vault_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vaults = repository(tmp_path)

    def fail_enumeration() -> tuple[UUID, ...]:
        raise VaultError("vault-enumeration-failed")

    monkeypatch.setattr(vaults, "conversation_ids", fail_enumeration)

    with pytest.raises(PrivacyRuntimeError, match="vault-enumeration-failed"):
        ResponsesRuntime.prepare(
            repository=vaults,
            registry=BindingRegistry(tmp_path),
            detector=NoopDetector(),
            policy=ToolPolicy.DEFAULT,
            resume_identity=None,
            clock=lambda: NOW,
            identifier_factory=lambda: NEW_ID,
        )

    assert not (tmp_path / "vaults" / f"{NEW_ID}.vault").exists()


def test_damaged_unrelated_vault_does_not_block_new_conversation(tmp_path: Path) -> None:
    vaults = repository(tmp_path)
    vaults.create(ConversationState.new(STALE_ID, mode=SubstitutionMode.ALIAS, now=NOW))
    (tmp_path / "vaults" / f"{STALE_ID}.vault").write_bytes(b"damaged")

    prepared = ResponsesRuntime.prepare(
        repository=vaults,
        registry=BindingRegistry(tmp_path),
        detector=NoopDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=None,
        clock=lambda: NOW,
        identifier_factory=lambda: NEW_ID,
    )

    assert prepared.conversation_id == NEW_ID
    assert (tmp_path / "vaults" / f"{STALE_ID}.vault").read_bytes() == b"damaged"


def test_expired_vault_cleanup_prunes_only_its_native_binding(tmp_path: Path) -> None:
    vaults = repository(tmp_path)
    registry = BindingRegistry(tmp_path)
    vaults.create(
        ConversationState.new(STALE_ID, mode=SubstitutionMode.ALIAS, now=NOW - timedelta(days=30))
    )
    vaults.create(ConversationState.new(ACTIVE_ID, mode=SubstitutionMode.ALIAS, now=NOW))
    registry.bind("claude", str(STALE_ID), STALE_ID)
    registry.bind("claude", str(ACTIVE_ID), ACTIVE_ID)

    MessagesRuntime.prepare(
        repository=vaults,
        registry=registry,
        detector=NoopDetector(),
        policy=ToolPolicy.DEFAULT,
        resume_identity=None,
        clock=lambda: NOW,
        identifier_factory=lambda: NEW_ID,
        native_identifier_factory=lambda: NATIVE_ID,
    )

    assert registry.lookup("claude", str(STALE_ID)) is None
    assert registry.lookup("claude", str(ACTIVE_ID)) == ACTIVE_ID
