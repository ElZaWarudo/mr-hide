from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.mark.compatibility
def test_manifest_boundaries_match_required_workflow_matrix() -> None:
    with (ROOT / "src" / "mr_hide" / "compatibility.toml").open("rb") as source:
        manifest = tomllib.load(source)
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(
        encoding="utf-8"
    )

    for matrix in manifest["compatibility_matrix"]:
        for version in matrix["versions"]:
            assert workflow.count(f'version: "{version}"') == len(matrix["platforms"])
        for platform in matrix["platforms"]:
            runner = "windows-latest" if platform == "windows" else "ubuntu-latest"
            assert runner in workflow


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
        for path in ("docs/compatibility.md", "docs/traffic-boundary.md")
    )
    assert "COMPATIBILITY_KEY_SENTINEL" not in rendered
    assert "Return exactly CONTRACT_OK" not in rendered
    assert "privacy-complete" in rendered
