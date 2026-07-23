"""Run deterministic local release-readiness checks without publishing."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[1]
TIMEOUT_SECONDS = 900


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    command: tuple[str, ...]


def _run(check: Check) -> None:
    completed = subprocess.run(
        check.command,
        cwd=ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"release check failed: {check.name}")
    print(f"pass: {check.name}")


def _base_checks(uv: str) -> tuple[Check, ...]:
    python = sys.executable
    return (
        Check("lock", (uv, "lock", "--check")),
        Check("ruff", (python, "-m", "ruff", "check", ".")),
        Check("mypy", (python, "-m", "mypy")),
        Check("workflow-yaml", (python, "scripts/check_workflow_yaml.py")),
        Check(
            "hermetic-tests",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "-m",
                "not compatibility and not nlp_models and not system_keyring",
            ),
        ),
        Check(
            "evidence-tests",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "tests/compatibility/test_evidence.py",
                "-m",
                "compatibility",
            ),
        ),
        Check("alias-benchmark", (python, "scripts/bench_aliases.py", "--check")),
        Check(
            "generated-evidence",
            (python, "scripts/compatibility/render_evidence.py", "--check"),
        ),
        Check("patch-whitespace", ("git", "diff", "--check")),
    )


def _find_tool(name: str) -> str | None:
    discovered = shutil.which(name)
    if discovered is not None:
        return discovered
    suffix = ".exe" if sys.platform == "win32" else ""
    sibling = Path(sys.executable).with_name(f"{name}{suffix}")
    return str(sibling) if sibling.is_file() else None


def run(*, fast: bool) -> None:
    uv = _find_tool("uv")
    if uv is None:
        raise RuntimeError("release check requires uv on PATH")
    for check in _base_checks(uv):
        _run(check)
    if not fast:
        with tempfile.TemporaryDirectory(prefix=".release-readiness-", dir=ROOT) as raw:
            output = Path(raw)
            requirements = output / "audit-requirements.txt"
            _run(
                Check(
                    "dependency-export",
                    (
                        uv,
                        "export",
                        "--locked",
                        "--all-extras",
                        "--no-emit-project",
                        "--format",
                        "requirements-txt",
                        "--output-file",
                        str(requirements),
                    ),
                )
            )
            uvx = _find_tool("uvx")
            if uvx is None:
                raise RuntimeError("release check requires uvx on PATH")
            _run(
                Check(
                    "dependency-audit",
                    (
                        uvx,
                        "--from",
                        "pip-audit==2.10.1",
                        "pip-audit",
                        "-r",
                        str(requirements),
                        "--progress-spinner",
                        "off",
                    ),
                )
            )
            _run(Check("build", (sys.executable, "-m", "build", "--outdir", str(output))))
            _run(
                Check(
                    "distribution-smoke",
                    (sys.executable, "scripts/verify_wheel.py", str(output)),
                )
            )
    print("release-readiness: local-pass")
    print("cross-platform-status: conditional; required Linux CI cells are unobserved locally")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip dependency audit and clean distribution installation.",
    )
    arguments = parser.parse_args()
    try:
        run(fast=arguments.fast)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
