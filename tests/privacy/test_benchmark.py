from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_synthetic_alias_benchmark_is_deterministic_and_truthful() -> None:
    root = Path(__file__).parents[2]
    command = (sys.executable, str(root / "scripts" / "bench_aliases.py"), "--check")

    first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    second = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    report = json.loads(first)

    assert first == second
    assert report["metric"] == "utf8-bytes"
    assert report["entities"] == 3
    assert report["occurrences"] == 12
    assert report["claimed_savings"] > 0
