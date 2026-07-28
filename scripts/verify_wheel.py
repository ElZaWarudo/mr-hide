"""Install one built wheel into a clean environment and exercise public resources."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

INSTALL_TIMEOUT_SECONDS = 600
SMOKE_TIMEOUT_SECONDS = 60


def verify_wheel(distribution_directory: Path) -> None:
    wheels = tuple(distribution_directory.glob("mr_hide-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one Mr Hide wheel, found {len(wheels)}.")
    source_archives = tuple(distribution_directory.glob("mr_hide-*.tar.gz"))
    if len(source_archives) != 1:
        raise RuntimeError(
            f"Expected one Mr Hide source archive, found {len(source_archives)}."
        )
    _verify_archive_contents(wheels[0], source_archives[0])

    with tempfile.TemporaryDirectory(prefix="mr-hide-wheel-") as temporary_directory:
        environment = Path(temporary_directory)
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = scripts / ("python.exe" if sys.platform == "win32" else "python")
        command = scripts / ("mr-hide.exe" if sys.platform == "win32" else "mr-hide")
        subprocess.run(
            (str(python), "-m", "pip", "install", str(wheels[0])),
            check=True,
            timeout=INSTALL_TIMEOUT_SECONDS,
        )
        console_version = _output(command, "--version")
        module_version = _output(python, "-m", "mr_hide", "--version")
        if console_version != module_version:
            raise RuntimeError("Console and module version output differ.")
        _output(command, "compatibility", "--json-output")
        _output(
            python,
            "-c",
            (
                "from importlib.resources import files; "
                "from importlib.metadata import version; "
                "from mr_hide import __version__; "
                "from mr_hide.policy import decide_policy; "
                "from mr_hide.privacy import MappingTable; "
                "import mr_hide.protocols.messages as messages_protocol; "
                "from mr_hide.protocols.responses import ResponsesRuntime, transform_request_json; "
                "from mr_hide.runtime.privacy import PrivacyRuntime; "
                "from mr_hide.state import BindingRegistry, ConversationService; "
                "from mr_hide.state import VaultCodec, VaultRepository; "
                "assert MappingTable().records == (); "
                "assert messages_protocol.transform_request_json; "
                "assert decide_policy and transform_request_json and ResponsesRuntime; "
                "assert messages_protocol.MessagesRuntime and PrivacyRuntime; "
                "assert BindingRegistry and ConversationService; "
                "assert VaultCodec and VaultRepository; "
                "assert version('mr-hide') == __version__; "
                "assert files('mr_hide').joinpath('py.typed').is_file()"
            ),
        )


def _verify_archive_contents(wheel: Path, source_archive: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = tuple(archive.namelist())
    with tarfile.open(source_archive, mode="r:gz") as archive:
        source_names = tuple(member.name for member in archive.getmembers())

    wheel_required = (
        "mr_hide/compatibility.toml",
        "mr_hide/py.typed",
        "mr_hide/protocols/messages/handler.py",
        "mr_hide/protocols/responses/handler.py",
        "mr_hide/runtime/privacy.py",
    )
    for required in wheel_required:
        if required not in wheel_names:
            raise RuntimeError(f"Wheel is missing required content: {required}")
    if not any(name.endswith(".dist-info/licenses/LICENSE") for name in wheel_names):
        raise RuntimeError("Wheel is missing the packaged license.")

    source_required = (
        "/README.md",
        "/LICENSE",
        "/pyproject.toml",
        "/scripts/check_release_readiness.py",
        "/tests/acceptance/test_mvp_matrix.py",
    )
    for suffix in source_required:
        if not any(name.endswith(suffix) for name in source_names):
            raise RuntimeError(f"Source archive is missing required content: {suffix[1:]}")

    forbidden = (".vault", "bindings.json", ".master-key", ".env", "__pycache__", ".pyc")
    for name in (*wheel_names, *source_names):
        lowered = name.casefold()
        if any(marker in lowered for marker in forbidden):
            raise RuntimeError("Distribution contains forbidden local-state content.")


def _output(command: Path, *args: str) -> str:
    completed = subprocess.run(
        (str(command), *args),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=SMOKE_TIMEOUT_SECONDS,
    )
    return completed.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution_directory", type=Path)
    arguments = parser.parse_args()
    verify_wheel(arguments.distribution_directory)


if __name__ == "__main__":
    main()
