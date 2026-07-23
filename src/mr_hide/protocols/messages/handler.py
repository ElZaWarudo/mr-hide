"""Conversation-scoped Anthropic Messages runtime composition."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mr_hide.policy import ToolPolicy
from mr_hide.privacy.detection import Detector
from mr_hide.runtime.privacy import PrivacyRuntime, PrivacyRuntimeError
from mr_hide.state.bindings import BindingRegistry
from mr_hide.state.repository import VaultRepository

MessagesRuntimeError = PrivacyRuntimeError


class MessagesRuntime(PrivacyRuntime):
    """Bind one launched Claude process to exactly one encrypted conversation."""

    @classmethod
    def prepare(
        cls,
        *,
        repository: VaultRepository,
        registry: BindingRegistry,
        detector: Detector,
        policy: ToolPolicy,
        resume_identity: str | None,
        bypass: bool = False,
        bypass_warning_accepted: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        identifier_factory: Callable[[], UUID] = uuid4,
        native_identifier_factory: Callable[[], UUID] = uuid4,
    ) -> MessagesRuntime:
        new_identity = None
        if resume_identity is None:
            new_identity = str(native_identifier_factory())
        return super()._prepare(
            client="claude",
            repository=repository,
            registry=registry,
            detector=detector,
            policy=policy,
            resume_identity=resume_identity,
            new_native_identity=new_identity,
            bypass=bypass,
            bypass_warning_accepted=bypass_warning_accepted,
            clock=clock,
            identifier_factory=identifier_factory,
        )
