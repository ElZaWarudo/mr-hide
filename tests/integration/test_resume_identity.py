from __future__ import annotations

import pytest

from mr_hide.clients import ClaudeAdapter, CodexAdapter


@pytest.mark.parametrize(
    "args,expected",
    [
        (("resume", "codex-session-id"), "codex-session-id"),
        (("exec", "resume", "codex-exec-session-id"), "codex-exec-session-id"),
        (("resume", "--last"), None),
        (("exec", "resume", "--json", "codex-option-session-id"), "codex-option-session-id"),
        (
            ("exec", "resume", "--model", "gpt-5", "codex-model-session-id"),
            "codex-model-session-id",
        ),
        (("--model", "gpt-5", "resume", "ordered-id", "prompt"), "ordered-id"),
    ],
)
def test_codex_resume_identity(args: tuple[str, ...], expected: str | None) -> None:
    assert CodexAdapter().resume_identity(args) == expected


@pytest.mark.parametrize(
    "args,expected",
    [
        (("--resume", "claude-session-id"), "claude-session-id"),
        (("-r", "claude-short-id"), "claude-short-id"),
        (("--resume=claude-inline-id",), "claude-inline-id"),
        (("--continue",), None),
        (("-c",), None),
    ],
)
def test_claude_resume_identity(args: tuple[str, ...], expected: str | None) -> None:
    assert ClaudeAdapter().resume_identity(args) == expected


def test_build_spec_exposes_same_native_resume_identity() -> None:
    spec = ClaudeAdapter().build_launch_spec(
        executable="claude",
        endpoint="http://127.0.0.1:40002",
        client_args=("--resume", "stable-native-id", "prompt"),
        parent_env={},
    )

    assert spec.resume_identity == "stable-native-id"
