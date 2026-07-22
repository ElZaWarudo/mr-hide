from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from mr_hide.compatibility import check_client_version
from tests.compatibility.conftest import contract_upstream
from tests.fixtures.client_contracts import CONTRACT_REPLY


@pytest.mark.compatibility
@pytest.mark.asyncio
async def test_pinned_codex_completes_responses_round_trip(tmp_path: Path) -> None:
    expected = os.environ.get("MR_HIDE_EXPECT_CODEX_VERSION")
    if expected is None:
        pytest.skip("set MR_HIDE_EXPECT_CODEX_VERSION for a pinned real-client run")
    assert str(check_client_version("codex").detected) == expected
    environment = dict(os.environ)
    environment["OPENAI_API_KEY"] = "COMPATIBILITY_KEY_SENTINEL"
    environment["CODEX_HOME"] = str(tmp_path / "codex-home")
    Path(environment["CODEX_HOME"]).mkdir()

    async with contract_upstream() as upstream:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "mr_hide",
            "codex",
            "--upstream",
            upstream,
            "--",
            "--disable",
            "plugins",
            "--disable",
            "remote_plugin",
            "--disable",
            "apps",
            "exec",
            "--skip-git-repo-check",
            "--ignore-user-config",
            "--sandbox",
            "read-only",
            "--model",
            "gpt-5.1-codex-mini",
            "Return exactly CONTRACT_OK",
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=90)

    combined = stdout + stderr
    assert process.returncode == 0, f"Codex exited with {process.returncode}"
    assert CONTRACT_REPLY.encode() in combined
    assert b"COMPATIBILITY_KEY_SENTINEL" not in combined
