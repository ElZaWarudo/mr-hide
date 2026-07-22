from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from mr_hide.clients.claude import ClaudeAdapter
from mr_hide.runtime.models import SupervisorResult
from mr_hide.runtime.supervisor import supervise_launch

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fake_client.py"


@pytest.mark.asyncio
async def test_concurrent_launches_keep_endpoints_and_state_isolated(tmp_path: Path) -> None:
    records = (tmp_path / "first.json", tmp_path / "second.json")

    async def launch(record: Path, identity: str) -> SupervisorResult:
        return await supervise_launch(
            adapter=ClaudeAdapter(),
            executable=sys.executable,
            upstream=f"http://upstream.test/{identity}",
            client_args=(
                str(FIXTURE),
                "--runtime-record",
                str(record),
                "--probe-endpoint-env",
                "ANTHROPIC_BASE_URL",
                "--sleep",
                "0.1",
                "--resume",
                identity,
            ),
            parent_env={**os.environ, "LAUNCH_ID": identity},
        )

    first, second = await asyncio.gather(
        launch(records[0], "native-first"),
        launch(records[1], "native-second"),
    )
    captured = [json.loads(path.read_text(encoding="utf-8")) for path in records]

    assert first.endpoint != second.endpoint
    assert captured[0]["endpoint"] == first.endpoint
    assert captured[1]["endpoint"] == second.endpoint
    assert first.resume_identity == "native-first"
    assert second.resume_identity == "native-second"
    assert all(item["probe_status"] == 404 for item in captured)
