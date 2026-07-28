from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
from pathlib import Path

import keyring
import pytest
from keyring.errors import PasswordDeleteError

from mr_hide.compatibility import check_client_version
from tests.compatibility.conftest import contract_upstream
from tests.fixtures.client_contracts import CONTRACT_REPLY


@pytest.mark.compatibility
@pytest.mark.asyncio
async def test_pinned_codex_completes_responses_round_trip(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    expected = os.environ.get("MR_HIDE_EXPECT_CODEX_VERSION")
    if expected is None:
        pytest.skip("set MR_HIDE_EXPECT_CODEX_VERSION for a pinned real-client run")
    assert str(check_client_version("codex").detected) == expected
    environment = dict(os.environ)
    environment["OPENAI_API_KEY"] = "COMPATIBILITY_KEY_SENTINEL"
    environment["CODEX_HOME"] = str(tmp_path / "codex-home")
    environment["MR_HIDE_STATE_DIR"] = str(tmp_path / "mr-hide-state")
    service = f"mr-hide-compat-{tmp_path.name}"
    environment["MR_HIDE_KEYRING_SERVICE"] = service

    def cleanup_key() -> None:
        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(service, "installation-master-key")

    request.addfinalizer(cleanup_key)
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
            "--json",
            "Return exactly CONTRACT_OK",
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=90)

    combined = stdout + stderr
    assert process.returncode == 0, (
        f"Codex exited with {process.returncode}:\n"
        f"{combined.decode('utf-8', errors='replace')}"
    )
    assert CONTRACT_REPLY.encode() in combined, combined.decode("utf-8", errors="replace")
    assert b"COMPATIBILITY_KEY_SENTINEL" not in combined
    thread_id = next(
        str(event["thread_id"])
        for line in stdout.decode("utf-8").splitlines()
        if (event := json.loads(line)).get("type") == "thread.started"
    )

    async with contract_upstream() as upstream:
        resumed = await asyncio.create_subprocess_exec(
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
            "resume",
            "--json",
            thread_id,
            "Return exactly CONTRACT_OK",
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        resumed_stdout, resumed_stderr = await asyncio.wait_for(
            resumed.communicate(), timeout=90
        )

    resumed_combined = resumed_stdout + resumed_stderr
    assert resumed.returncode == 0, f"Codex resume exited with {resumed.returncode}"
    assert CONTRACT_REPLY.encode() in resumed_combined, resumed_combined.decode(
        "utf-8", errors="replace"
    )
    assert thread_id.encode() not in resumed_stderr
    assert b"COMPATIBILITY_KEY_SENTINEL" not in resumed_combined
