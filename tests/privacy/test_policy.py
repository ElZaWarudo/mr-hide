from __future__ import annotations

import pytest

from mr_hide.policy import (
    ContentKind,
    Direction,
    PolicyAction,
    PolicyError,
    ToolPolicy,
    decide_policy,
)
from mr_hide.privacy.mapping import SubstitutionMode


@pytest.mark.parametrize("policy", tuple(ToolPolicy))
@pytest.mark.parametrize("kind", tuple(ContentKind))
def test_every_local_boundary_restores_known_mappings(
    policy: ToolPolicy,
    kind: ContentKind,
) -> None:
    decision = decide_policy(policy, Direction.TO_LOCAL, kind)

    assert decision.action is PolicyAction.RESTORE_KNOWN
    assert decision.warning_code is None


@pytest.mark.parametrize("policy", tuple(ToolPolicy))
def test_conversation_text_is_always_protected_toward_provider(
    policy: ToolPolicy,
) -> None:
    decision = decide_policy(policy, Direction.TO_PROVIDER, ContentKind.CONVERSATION)

    assert decision.action is PolicyAction.PROTECT
    assert decision.substitution_mode is (
        SubstitutionMode.COMPATIBILITY
        if policy is ToolPolicy.TOOL_COMPATIBILITY
        else SubstitutionMode.ALIAS
    )


@pytest.mark.parametrize("kind", tuple(ContentKind)[1:])
def test_default_tool_traffic_passes_through_with_warning(kind: ContentKind) -> None:
    decision = decide_policy(ToolPolicy.DEFAULT, Direction.TO_PROVIDER, kind)

    assert decision.action is PolicyAction.PASS_THROUGH
    assert decision.warning_code == "tool-data-unprotected"


@pytest.mark.parametrize(
    ("policy", "mode"),
    (
        (ToolPolicy.SAFE_TOOL_CALLS, SubstitutionMode.ALIAS),
        (ToolPolicy.TOOL_COMPATIBILITY, SubstitutionMode.COMPATIBILITY),
    ),
)
@pytest.mark.parametrize("kind", tuple(ContentKind)[1:])
def test_nondefault_tool_traffic_is_protected(
    policy: ToolPolicy,
    mode: SubstitutionMode,
    kind: ContentKind,
) -> None:
    decision = decide_policy(policy, Direction.TO_PROVIDER, kind)

    assert decision.action is PolicyAction.PROTECT
    assert decision.substitution_mode is mode
    assert decision.warning_code is None


@pytest.mark.parametrize(
    "arguments",
    (
        ("default", Direction.TO_PROVIDER, ContentKind.CONVERSATION),
        (ToolPolicy.DEFAULT, "to-provider", ContentKind.CONVERSATION),
        (ToolPolicy.DEFAULT, Direction.TO_PROVIDER, "conversation"),
    ),
)
def test_invalid_policy_inputs_fail_closed(arguments: tuple[object, object, object]) -> None:
    with pytest.raises(PolicyError, match="invalid-tool-policy"):
        decide_policy(*arguments)  # type: ignore[arg-type]
