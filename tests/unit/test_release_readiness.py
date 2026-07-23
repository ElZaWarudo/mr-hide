from __future__ import annotations

from pathlib import Path

import pytest

import scripts.check_release_readiness as readiness


@pytest.mark.parametrize(
    ("fast", "expected"),
    (
        (
            True,
            {
                "lock",
                "ruff",
                "mypy",
                "workflow-yaml",
                "hermetic-tests",
                "evidence-tests",
            },
        ),
        (
            False,
            {
                "lock",
                "ruff",
                "mypy",
                "workflow-yaml",
                "hermetic-tests",
                "evidence-tests",
                "dependency-audit",
                "build",
                "distribution-smoke",
            },
        ),
    ),
)
def test_readiness_modes_are_local_and_non_publishing(
    monkeypatch: pytest.MonkeyPatch,
    fast: bool,
    expected: set[str],
) -> None:
    checks: list[readiness.Check] = []

    def executable(name: str) -> str:
        return str(Path("tools") / name)

    monkeypatch.setattr(readiness.shutil, "which", executable)
    monkeypatch.setattr(readiness, "_run", checks.append)

    readiness.run(fast=fast)

    names = {check.name for check in checks}
    commands = " ".join(part for check in checks for part in check.command).casefold()
    assert expected <= names
    assert not ({"push", "publish", "upload", "workflow", "release"} & set(commands.split()))
