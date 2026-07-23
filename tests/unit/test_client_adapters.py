from __future__ import annotations

from types import MappingProxyType

import pytest

from mr_hide.clients import ClaudeAdapter, CodexAdapter, LaunchConflict


@pytest.mark.parametrize(
    "adapter",
    [CodexAdapter(), ClaudeAdapter()],
)
def test_launch_specs_preserve_unrelated_arguments(adapter: CodexAdapter | ClaudeAdapter) -> None:
    client_args = (
        "--verbose",
        "-p",
        "café",
        r"C:\path with spaces\file.txt",
        "--tag=a=b",
        "--",
        "literal",
    )

    spec = adapter.build_launch_spec(
        executable=adapter.name,
        endpoint="http://127.0.0.1:43123",
        client_args=client_args,
        parent_env={"PATH": "synthetic-path", "SESSION_SENTINEL": "kept"},
    )

    assert spec.client_args == client_args
    assert spec.env["SESSION_SENTINEL"] == "kept"
    assert isinstance(spec.env, MappingProxyType)


def test_codex_uses_one_run_config_and_preserves_codex_home() -> None:
    parent = {"PATH": "synthetic", "CODEX_HOME": r"C:\native-codex-home"}

    spec = CodexAdapter().build_launch_spec(
        executable="codex",
        endpoint="http://127.0.0.1:40001",
        client_args=("resume", "session-123"),
        parent_env=parent,
    )

    assert spec.argv == (
        "codex",
        "--config",
        'openai_base_url="http://127.0.0.1:40001/v1"',
        "resume",
        "session-123",
    )
    assert spec.env["CODEX_HOME"] == parent["CODEX_HOME"]
    assert parent == {"PATH": "synthetic", "CODEX_HOME": r"C:\native-codex-home"}


def test_claude_uses_child_only_environment_and_preserves_auth() -> None:
    parent = {
        "PATH": "synthetic",
        "ANTHROPIC_API_KEY": "credential-sentinel",
        "CLAUDE_CONFIG_DIR": "/native/claude",
    }

    spec = ClaudeAdapter().build_launch_spec(
        executable="claude",
        endpoint="http://127.0.0.1:40002",
        client_args=("--resume", "session-456"),
        parent_env=parent,
    )

    assert spec.argv == ("claude", "--resume", "session-456")
    assert spec.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:40002"
    assert spec.env["ANTHROPIC_API_KEY"] == "credential-sentinel"
    assert spec.env["CLAUDE_CONFIG_DIR"] == "/native/claude"
    assert "ANTHROPIC_BASE_URL" not in parent


@pytest.mark.parametrize(
    "args",
    [
        ("--config", 'openai_base_url="https://other.example"'),
        ('--config=openai_base_url="https://other.example"',),
        ("-c", 'model_providers.custom.base_url="https://other.example"'),
    ],
)
def test_codex_rejects_endpoint_conflicts(args: tuple[str, ...]) -> None:
    with pytest.raises(LaunchConflict, match="endpoint"):
        CodexAdapter().build_launch_spec(
            executable="codex",
            endpoint="http://127.0.0.1:40001",
            client_args=args,
            parent_env={},
        )


def test_claude_replaces_inherited_base_url_only_in_child_copy() -> None:
    parent = {"ANTHROPIC_BASE_URL": "https://old.example", "TOKEN": "kept"}

    spec = ClaudeAdapter().build_launch_spec(
        executable="claude",
        endpoint="http://127.0.0.1:40002",
        client_args=(),
        parent_env=parent,
    )

    assert spec.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:40002"
    assert parent["ANTHROPIC_BASE_URL"] == "https://old.example"


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:40001",
        "http://0.0.0.0:40001",
        "http://user:password@127.0.0.1:40001",
        "http://127.0.0.1",
        "http://127.0.0.1:40001/path",
    ],
)
def test_adapters_reject_non_loopback_origin_endpoints(endpoint: str) -> None:
    with pytest.raises(LaunchConflict, match="loopback"):
        CodexAdapter().build_launch_spec(
            executable="codex",
            endpoint=endpoint,
            client_args=(),
            parent_env={},
        )


def test_native_boundary_stops_resume_and_conflict_interpretation() -> None:
    codex = CodexAdapter()
    claude = ClaudeAdapter()

    assert codex.resume_identity(("--", "resume", "literal-id")) is None
    assert claude.resume_identity(("--", "--resume", "literal-id")) is None
    spec = codex.build_launch_spec(
        executable="codex",
        endpoint="http://127.0.0.1:40001",
        client_args=("--", "--config", "openai_base_url=literal"),
        parent_env={},
    )
    assert spec.client_args == ("--", "--config", "openai_base_url=literal")


@pytest.mark.parametrize(
    "args",
    [
        ("--continue",),
        ("-c",),
        ("--session-id", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ("--session-id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",),
        ("--fork-session",),
        ("--resume", "one", "-r", "two"),
    ],
)
def test_claude_rejects_ambiguous_or_launcher_owned_session_flags(
    args: tuple[str, ...],
) -> None:
    with pytest.raises(LaunchConflict):
        ClaudeAdapter().build_launch_spec(
            executable="claude",
            endpoint="http://127.0.0.1:40002",
            client_args=args,
            parent_env={},
        )
