from __future__ import annotations

import pytest
from click.testing import CliRunner
from packaging.version import Version

from mr_hide import __version__
from mr_hide.cli import cli
from mr_hide.compatibility import VersionCheck


def supported_check(client: str, **_kwargs: object) -> VersionCheck:
    return VersionCheck(
        client=client,
        executable=client,
        detected=Version("1.0.0"),
        tested_range=">=1",
        evidence_status="candidate",
        supported=True,
        override=False,
    )


def test_root_help_exposes_only_foundation_commands() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert {"codex", "claude", "compatibility", "doctor"} <= set(result.output.split())
    assert "privacy-mode" not in result.output
    assert "presidio" not in result.output.lower()


def test_module_version_matches_package_version() -> None:
    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"mr-hide, version {__version__}"


def test_launch_requires_upstream() -> None:
    result = CliRunner().invoke(cli, ["codex", "--", "resume", "session-123"])

    assert result.exit_code == 2
    assert "--upstream" in result.output


def test_launch_requires_explicit_client_argument_boundary() -> None:
    result = CliRunner().invoke(
        cli,
        ["codex", "--upstream", "https://api.example.test", "resume", "session-123"],
    )

    assert result.exit_code == 2
    assert "separate client arguments with --" in result.output


def test_help_documents_explicit_boundary_without_running_client() -> None:
    result = CliRunner().invoke(cli, ["claude", "--help"])

    assert result.exit_code == 0
    assert "-- CLIENT_ARGS" in result.output
    assert "--allow-untested" in result.output


def test_doctor_reports_credential_presence_without_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "OPENAI_SECRET_SENTINEL")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ANTHROPIC_SECRET_SENTINEL")
    monkeypatch.setattr(
        "mr_hide.cli.check_client_version",
        supported_check,
    )

    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0
    assert "OPENAI_API_KEY: present" in result.output
    assert "ANTHROPIC_API_KEY: present" in result.output
    assert "OPENAI_SECRET_SENTINEL" not in result.output
    assert "ANTHROPIC_SECRET_SENTINEL" not in result.output


def test_cli_rejects_client_endpoint_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)

    result = CliRunner().invoke(
        cli,
        [
            "codex",
            "--upstream",
            "https://api.example.test",
            "--",
            "--config",
            'openai_base_url="https://other.example"',
        ],
    )

    assert result.exit_code == 2
    assert "endpoint configuration" in result.output


def test_preflight_never_echoes_upstream_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)

    result = CliRunner().invoke(
        cli,
        [
            "claude",
            "--upstream",
            "https://api.example.test?token=UPSTREAM_SECRET_SENTINEL",
            "--",
        ],
    )

    assert result.exit_code == 1
    assert "explicit upstream" in result.output
    assert "UPSTREAM_SECRET_SENTINEL" not in result.output
