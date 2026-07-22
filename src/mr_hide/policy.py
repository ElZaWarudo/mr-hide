"""Protocol-neutral privacy decisions for conversation and tool text."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mr_hide.privacy.mapping import SubstitutionMode


class ToolPolicy(StrEnum):
    DEFAULT = "default"
    SAFE_TOOL_CALLS = "safe-tool-calls"
    TOOL_COMPATIBILITY = "tool-compatibility"


class Direction(StrEnum):
    TO_PROVIDER = "to-provider"
    TO_LOCAL = "to-local"


class ContentKind(StrEnum):
    CONVERSATION = "conversation"
    TOOL_DEFINITION = "tool-definition"
    TOOL_ARGUMENT = "tool-argument"
    TOOL_RESULT = "tool-result"
    TOOL_HISTORY = "tool-history"


class PolicyAction(StrEnum):
    PROTECT = "protect"
    RESTORE_KNOWN = "restore-known"
    PASS_THROUGH = "pass-through"


class PolicyError(RuntimeError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: PolicyAction
    substitution_mode: SubstitutionMode
    warning_code: str | None = None


def decide_policy(
    policy: ToolPolicy,
    direction: Direction,
    content_kind: ContentKind,
) -> PolicyDecision:
    """Return the domain action without inspecting provider wire formats."""

    if (
        not isinstance(policy, ToolPolicy)
        or not isinstance(direction, Direction)
        or not isinstance(content_kind, ContentKind)
    ):
        raise PolicyError("invalid-tool-policy")

    mode = (
        SubstitutionMode.COMPATIBILITY
        if policy is ToolPolicy.TOOL_COMPATIBILITY
        else SubstitutionMode.ALIAS
    )
    if direction is Direction.TO_LOCAL:
        return PolicyDecision(PolicyAction.RESTORE_KNOWN, mode)
    if content_kind is ContentKind.CONVERSATION:
        return PolicyDecision(PolicyAction.PROTECT, mode)
    if policy is ToolPolicy.DEFAULT:
        return PolicyDecision(
            PolicyAction.PASS_THROUGH,
            mode,
            warning_code="tool-data-unprotected",
        )
    return PolicyDecision(PolicyAction.PROTECT, mode)
