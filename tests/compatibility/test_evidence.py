from __future__ import annotations

import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parents[2]
CompatibilityCell = tuple[str, str, str]

PLATFORM_BY_RUNNER = {
    "ubuntu-latest": "linux",
    "windows-latest": "windows",
}


def _manifest_cells(manifest: dict[str, Any]) -> Counter[CompatibilityCell]:
    return Counter(
        (matrix["client"], version, platform)
        for matrix in manifest["compatibility_matrix"]
        for version in matrix["versions"]
        for platform in matrix["platforms"]
    )


def _workflow_cells(workflow: dict[str, Any]) -> Counter[CompatibilityCell]:
    matrix = workflow["jobs"]["client-contract"]["strategy"]["matrix"]["include"]
    return Counter(
        (
            row["client"],
            str(row["version"]),
            PLATFORM_BY_RUNNER.get(row["os"], row["os"]),
        )
        for row in matrix
    )


def _assert_exact_cell_multiset(
    expected: Counter[CompatibilityCell],
    actual: Counter[CompatibilityCell],
) -> None:
    expected_duplicates = expected - Counter(expected.keys())
    actual_duplicates = actual - Counter(actual.keys())
    assert not expected_duplicates, (
        f"manifest contains duplicate compatibility cells: {expected_duplicates}"
    )
    assert not actual_duplicates, (
        f"workflow contains duplicate compatibility cells: {actual_duplicates}"
    )

    missing = expected - actual
    extra = actual - expected
    assert not missing, f"workflow is missing compatibility cells: {missing}"
    assert not extra, f"workflow contains extra compatibility cells: {extra}"


@pytest.mark.compatibility
def test_manifest_boundaries_match_required_workflow_matrix() -> None:
    with (ROOT / "src" / "mr_hide" / "compatibility.toml").open("rb") as source:
        manifest = tomllib.load(source)
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(
            encoding="utf-8"
        )
    )

    _assert_exact_cell_multiset(
        _manifest_cells(manifest),
        _workflow_cells(workflow),
    )

    required = {
        (matrix["client"], version, platform)
        for matrix in manifest["compatibility_matrix"]
        for version in matrix["versions"]
        for platform in matrix["platforms"]
    }
    observed = {
        (row["client"], row["version"], row["platform"])
        for row in manifest["observed_evidence"]
        if row["result"] == "pass"
    }
    assert required <= observed
    assert all(
        client["evidence_status"] == "verified"
        for client in manifest["clients"].values()
    )


@pytest.mark.parametrize(
    ("actual", "message"),
    [
        (Counter(), "missing compatibility cells"),
        (
            Counter({("codex", "1.0.0", "linux"): 2}),
            "duplicate compatibility cells",
        ),
        (
            Counter(
                {
                    ("codex", "1.0.0", "linux"): 1,
                    ("claude", "2.0.0", "windows"): 1,
                }
            ),
            "extra compatibility cells",
        ),
    ],
)
def test_exact_cell_multiset_rejects_workflow_drift(
    actual: Counter[CompatibilityCell],
    message: str,
) -> None:
    expected = Counter({("codex", "1.0.0", "linux"): 1})

    with pytest.raises(AssertionError, match=message):
        _assert_exact_cell_multiset(expected, actual)


@pytest.mark.compatibility
def test_generated_evidence_is_current_and_redacted() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/compatibility/render_evidence.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    rendered = "".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "docs/compatibility.md",
            "docs/traffic-boundary.md",
            "docs/release-readiness.md",
        )
    )
    assert "COMPATIBILITY_KEY_SENTINEL" not in rendered
    assert "Return exactly CONTRACT_OK" not in rendered
    assert "Supported Codex" in rendered
    assert "Release-ready for v0.1.0" in rendered
    assert "30343602093" in rendered
    assert "| claude | 2.1.217 | linux |" in rendered
