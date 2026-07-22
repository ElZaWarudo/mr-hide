"""Safe diagnostics that report presence and policy, never secret values."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

SENSITIVE_ENVIRONMENT_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AZURE_OPENAI_API_KEY",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "SSH_AUTH_SOCK",
    }
)
_SENSITIVE_NAME = re.compile(
    r"(?:^|_)(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?|AUTH)(?:_|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class EnvironmentDiagnostic:
    name: str
    present: bool


def environment_presence(environment: Mapping[str, str]) -> tuple[EnvironmentDiagnostic, ...]:
    """Describe only whether known credential variables are populated."""

    return tuple(
        EnvironmentDiagnostic(name, bool(environment.get(name)))
        for name in sorted(SENSITIVE_ENVIRONMENT_NAMES)
    )


def safe_probe_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Copy process settings needed for discovery without credential-bearing values."""

    return {
        name: value
        for name, value in environment.items()
        if name.upper() not in SENSITIVE_ENVIRONMENT_NAMES and not _SENSITIVE_NAME.search(name)
    }
