from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

import scripts.check_release_readiness as readiness
from scripts.compatibility.evidence import summarize_evidence
from scripts.compatibility.render_evidence import (
    render_compatibility,
    render_release_readiness,
)


@pytest.fixture
def compatibility_manifest() -> dict[str, Any]:
    return {
        "clients": {
            "codex": {
                "display_name": "Codex CLI",
                "supported": ">=0.144.4,<=0.145.0",
                "evidence_status": "verified",
                "evidence_note": "Recorded contract evidence.",
            }
        },
        "compatibility_matrix": [
            {
                "client": "codex",
                "versions": ["0.145.0"],
                "platforms": ["windows", "linux"],
                "flow": "protected launch and native resume",
                "routes": ["/v1/responses"],
                "status": "required",
            }
        ],
        "observed_evidence": [
            {
                "date": "2026-07-28",
                "client": "codex",
                "version": "0.145.0",
                "platform": platform,
                "flow": "protected launch and native resume",
                "result": "pass",
                "limitations": "Protocol-shaped local upstream.",
            }
            for platform in ("windows", "linux")
        ],
    }


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

    monkeypatch.setattr(shutil, "which", executable)
    monkeypatch.setattr(readiness, "_run", checks.append)

    readiness.run(fast=fast)

    names = {check.name for check in checks}
    commands = " ".join(part for check in checks for part in check.command).casefold()
    assert expected <= names
    assert not ({"push", "publish", "upload", "workflow", "release"} & set(commands.split()))


def test_recorded_compatibility_evidence_is_release_complete() -> None:
    assert readiness._compatibility_evidence_complete() is True


@pytest.mark.parametrize(
    ("scenario", "expected_pending"),
    (
        ("missing-cell", frozenset({("codex", "0.145.0", "linux")})),
        ("unverified-client", frozenset()),
    ),
)
def test_incomplete_evidence_keeps_release_conditional(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    compatibility_manifest: dict[str, Any],
    scenario: str,
    expected_pending: frozenset[tuple[str, str, str]],
) -> None:
    if scenario == "missing-cell":
        compatibility_manifest["observed_evidence"] = [
            row
            for row in compatibility_manifest["observed_evidence"]
            if row["platform"] != "linux"
        ]
    else:
        compatibility_manifest["clients"]["codex"]["evidence_status"] = "candidate"

    evidence = summarize_evidence(compatibility_manifest)
    assert evidence.complete is False
    assert evidence.pending == expected_pending

    monkeypatch.setattr(readiness, "load_evidence_manifest", lambda _: compatibility_manifest)
    monkeypatch.setattr(readiness, "_find_tool", lambda _: "uv")
    monkeypatch.setattr(readiness, "_base_checks", lambda _: ())
    readiness.run(fast=True)
    gate_output = capsys.readouterr().out
    assert "release-readiness: local-pass" in gate_output
    assert "cross-platform-status: conditional" in gate_output

    compatibility = render_compatibility(compatibility_manifest, evidence)
    release = render_release_readiness(compatibility_manifest, evidence)
    assert "## Candidate ranges" in compatibility
    assert "## Supported ranges" not in compatibility
    assert "**Conditional local pass.**" in release
    assert "**Release-ready for v0.1.0.**" not in release

    pending_rows = {
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in release.splitlines()
        if line.startswith("| codex ")
    }
    assert pending_rows == expected_pending
