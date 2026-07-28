from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mr_hide.compatibility import (
    ClientNotFound,
    MalformedClientVersion,
    UnsupportedClientVersion,
    _resolve_executable,
    check_client_version,
    load_manifest,
)

FAKE_CLIENT = Path(__file__).parents[1] / "fixtures" / "fake_client.py"


def fake_probe(version: str) -> tuple[str, tuple[str, ...]]:
    return sys.executable, (str(FAKE_CLIENT), "--version", version)


def test_manifest_contains_verified_release_ranges() -> None:
    manifest = load_manifest()

    assert set(manifest.clients) == {"codex", "claude"}
    assert str(manifest.clients["codex"].supported) == ">=0.144.4,<0.146.0"
    assert str(manifest.clients["claude"].supported) == ">=2.1.216,<=2.1.217"
    assert all(client.evidence_status == "verified" for client in manifest.clients.values())


@pytest.mark.parametrize("client,version", [("codex", "0.145.0"), ("claude", "2.1.217")])
def test_supported_stable_version_passes(client: str, version: str) -> None:
    executable, version_args = fake_probe(version)

    result = check_client_version(client, executable=executable, version_args=version_args)

    assert str(result.detected) == version
    assert result.supported is True
    assert result.override is False


@pytest.mark.parametrize(
    "version",
    ["0.1.0", "99.0.0", "0.145.0rc1"],
)
def test_unsupported_or_prerelease_version_blocks(version: str) -> None:
    executable, version_args = fake_probe(version)

    with pytest.raises(UnsupportedClientVersion, match="tested range"):
        check_client_version("codex", executable=executable, version_args=version_args)


def test_one_run_override_does_not_mutate_manifest() -> None:
    executable, version_args = fake_probe("99.0.0")
    before = load_manifest().clients["codex"].supported

    result = check_client_version(
        "codex",
        executable=executable,
        version_args=version_args,
        allow_untested=True,
    )

    assert result.supported is False
    assert result.override is True
    assert load_manifest().clients["codex"].supported == before


def test_malformed_version_blocks_without_echoing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    executable, version_args = fake_probe("not-a-version SECRET_VALUE")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SECRET_VALUE")

    with pytest.raises(MalformedClientVersion) as error:
        check_client_version("claude", executable=executable, version_args=version_args)

    assert "SECRET_VALUE" not in str(error.value)


def test_invalid_version_bytes_become_safe_malformed_error() -> None:
    with pytest.raises(MalformedClientVersion, match="stable Claude Code version"):
        check_client_version(
            "claude",
            executable=sys.executable,
            version_args=(str(FAKE_CLIENT), "--version-bytes"),
        )


def test_missing_binary_has_safe_diagnostic() -> None:
    with pytest.raises(ClientNotFound, match=r"(?i)codex") as error:
        check_client_version("codex", executable="definitely-missing-mr-hide-client")

    assert "PATH" in str(error.value)


def test_implicit_current_directory_executable_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "mr_hide.compatibility.shutil.which",
        lambda _executable: str(tmp_path / "codex.exe"),
    )
    monkeypatch.setattr(
        "mr_hide.compatibility.os.get_exec_path",
        lambda: [str(tmp_path / "explicit-bin")],
    )

    with pytest.raises(ClientNotFound, match="explicit PATH"):
        _resolve_executable("codex", "Codex")
