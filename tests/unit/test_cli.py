from __future__ import annotations

import pytest
from click.testing import CliRunner
from packaging.version import Version

from mr_hide import __version__
from mr_hide.cli import cli
from mr_hide.compatibility import VersionCheck
from mr_hide.diagnostics import ModelDiagnostic
from mr_hide.runtime.models import SupervisorResult
from mr_hide.security import KeyringCapability


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
    monkeypatch.setattr(
        "mr_hide.cli.probe_keyring",
        lambda: KeyringCapability(True, "approved.Backend", "available"),
    )
    monkeypatch.setattr(
        "mr_hide.cli.model_presence",
        lambda: (
            ModelDiagnostic("en", "en_core_web_sm", True),
            ModelDiagnostic("es", "es_core_news_sm", False),
        ),
    )

    result = CliRunner().invoke(cli, ["doctor"])

    assert result.exit_code == 0
    assert "OPENAI_API_KEY: present" in result.output
    assert "ANTHROPIC_API_KEY: present" in result.output
    assert "secure_store: available (approved.Backend; available)" in result.output
    assert "nlp_model_en: available (en_core_web_sm)" in result.output
    assert "nlp_model_es: unavailable (es_core_news_sm)" in result.output
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

    async def supervised(**_kwargs: object) -> SupervisorResult:
        return SupervisorResult(
            exit_code=0,
            endpoint="http://127.0.0.1:40123",
            resume_identity=None,
        )

    monkeypatch.setattr("mr_hide.cli.supervise_launch", supervised)

    result = CliRunner().invoke(
        cli,
        [
            "claude",
            "--upstream",
            "https://api.example.test?token=UPSTREAM_SECRET_SENTINEL",
            "--",
        ],
    )

    assert result.exit_code == 0
    assert "UPSTREAM_SECRET_SENTINEL" not in result.output


def test_cli_propagates_supervised_child_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)

    async def supervised(**_kwargs: object) -> SupervisorResult:
        return SupervisorResult(
            exit_code=23,
            endpoint="http://127.0.0.1:40124",
            resume_identity="native-session",
        )

    monkeypatch.setattr("mr_hide.cli.supervise_launch", supervised)

    result = CliRunner().invoke(
        cli,
        [
            "claude",
            "--upstream",
            "https://api.example.test",
            "--",
            "--resume",
            "native-session",
        ],
    )

    assert result.exit_code == 23
    assert result.output == ""


def test_codex_policy_is_visible_and_passed_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)
    class Prepared:
        bypassed = False

    prepared = Prepared()
    captured: dict[str, object] = {}

    def prepare(
        resume_identity: str | None,
        tool_policy: object,
        **kwargs: object,
    ) -> object:
        captured.update(
            resume_identity=resume_identity,
            tool_policy=tool_policy,
            **kwargs,
        )
        return prepared

    async def supervised(**kwargs: object) -> SupervisorResult:
        assert kwargs["responses_runtime"] is prepared
        return SupervisorResult(0, "http://127.0.0.1:40125", None)

    monkeypatch.setattr("mr_hide.cli._prepare_codex_runtime", prepare)
    monkeypatch.setattr("mr_hide.cli.supervise_launch", supervised)

    result = CliRunner().invoke(
        cli,
        [
            "codex",
            "--upstream",
            "https://api.example.test",
            "--tool-policy",
            "safe-tool-calls",
            "--",
            "exec",
            "prompt",
        ],
    )

    assert result.exit_code == 0
    assert "conversation: protected" in result.output
    assert "tool-policy: safe-tool-calls" in result.output
    assert "tool-data-unprotected" not in result.output
    assert str(captured["tool_policy"]) == "safe-tool-calls"


def test_codex_bypass_requires_visible_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)

    result = CliRunner().invoke(
        cli,
        [
            "codex",
            "--upstream",
            "https://api.example.test",
            "--bypass",
            "--",
        ],
    )

    assert result.exit_code == 2
    assert "--bypass requires --accept-bypass-warning" in result.output


def test_codex_ambiguous_resume_is_rejected_before_state_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mr_hide.cli.check_client_version", supported_check)

    result = CliRunner().invoke(
        cli,
        [
            "codex",
            "--upstream",
            "https://api.example.test",
            "--",
            "exec",
            "resume",
            "--last",
        ],
    )

    assert result.exit_code == 2
    assert "explicit canonical session UUID" in result.output
