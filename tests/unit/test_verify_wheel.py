from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import scripts.verify_wheel as wheel


def test_smoke_commands_allow_cold_dependency_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(stdout="ok")

    monkeypatch.setattr("scripts.verify_wheel.subprocess.run", run)

    assert wheel._output(Path("python"), "-m", "mr_hide", "--version") == "ok"
    assert captured["timeout"] == wheel.SMOKE_TIMEOUT_SECONDS == 60
