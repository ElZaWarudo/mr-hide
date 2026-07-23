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
async def test_pinned_claude_launch_and_resume_round_trip(
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    expected = os.environ.get("MR_HIDE_EXPECT_CLAUDE_VERSION")
    if expected is None:
        pytest.skip("set MR_HIDE_EXPECT_CLAUDE_VERSION for a pinned real-client run")
    assert str(check_client_version("claude").detected) == expected
    environment = dict(os.environ)
    environment.update(
        {
            "ANTHROPIC_API_KEY": "COMPATIBILITY_KEY_SENTINEL",
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude-home"),
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_TELEMETRY": "1",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "MR_HIDE_STATE_DIR": str(tmp_path / "mr-hide-state"),
        }
    )
    service = f"mr-hide-compat-{tmp_path.name}"
    environment["MR_HIDE_KEYRING_SERVICE"] = service

    def cleanup_key() -> None:
        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(service, "installation-master-key")

    request.addfinalizer(cleanup_key)
    Path(environment["CLAUDE_CONFIG_DIR"]).mkdir()

    captured_bodies: list[bytes] = []
    prompt = "Keep alice@example.com private and return exactly CONTRACT_OK"
    async with contract_upstream(captured_bodies) as upstream:
        first = await _run_claude(upstream, environment, prompt)
        payload = json.loads(first.decode())
        session_id = str(payload["session_id"])
        resumed = await _run_claude(upstream, environment, prompt, session_id=session_id)

    assert CONTRACT_REPLY.encode() in first
    assert CONTRACT_REPLY.encode() in resumed
    assert b"COMPATIBILITY_KEY_SENTINEL" not in first + resumed
    assert captured_bodies
    assert b"alice@example.com" not in b"".join(captured_bodies)


async def _run_claude(
    upstream: str,
    environment: dict[str, str],
    prompt: str,
    *,
    session_id: str | None = None,
) -> bytes:
    args = ["-p", prompt, "--output-format", "json", "--max-turns", "1"]
    if session_id is not None:
        args.extend(("--resume", session_id))
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "mr_hide",
        "claude",
        "--upstream",
        upstream,
        "--",
        *args,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=90)
    assert process.returncode == 0, f"Claude Code exited with {process.returncode}"
    return stdout
