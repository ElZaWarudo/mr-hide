from __future__ import annotations

import pytest

from mr_hide.diagnostics import environment_presence, model_presence, safe_probe_environment


def test_probe_environment_removes_credentials_and_native_state_paths() -> None:
    parent = {
        "PATH": "safe-path",
        "SYSTEMROOT": "safe-system-root",
        "OPENAI_API_KEY": "openai-secret",
        "ANTHROPIC_API_KEY": "anthropic-secret",
        "GITHUB_TOKEN": "github-secret",
        "SERVICE_PASSWORD": "password-secret",
        "SSH_AUTH_SOCK": "agent-socket",
        "CODEX_HOME": "codex-state",
        "CLAUDE_CONFIG_DIR": "claude-state",
    }

    probe = safe_probe_environment(parent)

    assert probe == {"PATH": "safe-path", "SYSTEMROOT": "safe-system-root"}
    assert parent["OPENAI_API_KEY"] == "openai-secret"
    assert parent["CODEX_HOME"] == "codex-state"


def test_presence_diagnostics_never_copy_values() -> None:
    diagnostics = environment_presence({"OPENAI_API_KEY": "secret-sentinel"})

    assert any(item.name == "OPENAI_API_KEY" and item.present for item in diagnostics)
    assert all("secret-sentinel" not in repr(item) for item in diagnostics)


def test_model_presence_reports_both_languages_without_loading_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "spacy.util.is_package",
        lambda package: package == "en_core_web_sm",
    )

    result = model_presence()

    assert [(item.language, item.available) for item in result] == [
        ("en", True),
        ("es", False),
    ]
