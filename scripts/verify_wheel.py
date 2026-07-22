"""Install one built wheel into a clean environment and exercise public resources."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def verify_wheel(distribution_directory: Path) -> None:
    wheels = tuple(distribution_directory.glob("mr_hide-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one Mr Hide wheel, found {len(wheels)}.")

    with tempfile.TemporaryDirectory(prefix="mr-hide-wheel-") as temporary_directory:
        environment = Path(temporary_directory)
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = scripts / ("python.exe" if sys.platform == "win32" else "python")
        command = scripts / ("mr-hide.exe" if sys.platform == "win32" else "mr-hide")
        subprocess.run(
            (str(python), "-m", "pip", "install", str(wheels[0])),
            check=True,
            timeout=180,
        )
        console_version = _output(command, "--version")
        module_version = _output(python, "-m", "mr_hide", "--version")
        if console_version != module_version:
            raise RuntimeError("Console and module version output differ.")
        _output(command, "compatibility", "--json-output")


def _output(command: Path, *args: str) -> str:
    completed = subprocess.run(
        (str(command), *args),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return completed.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution_directory", type=Path)
    arguments = parser.parse_args()
    verify_wheel(arguments.distribution_directory)


if __name__ == "__main__":
    main()
