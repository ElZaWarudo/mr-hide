"""Claude Code native-state-preserving adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from mr_hide.clients.base import ClientAdapter, LaunchConflict, LaunchSpec


class ClaudeAdapter(ClientAdapter):
    name = "claude"

    def build_launch_spec(
        self,
        *,
        executable: str,
        endpoint: str,
        client_args: Sequence[str],
        parent_env: Mapping[str, str],
    ) -> LaunchSpec:
        self.validate_local_endpoint(endpoint)
        args = tuple(client_args)
        self.validate_client_args(args)
        child_env = dict(parent_env)
        child_env["ANTHROPIC_BASE_URL"] = endpoint
        return LaunchSpec(
            argv=(executable, *args),
            client_args=args,
            env=MappingProxyType(child_env),
            resume_identity=self.resume_identity(args),
        )

    def resume_identity(self, client_args: Sequence[str]) -> str | None:
        args = self.interpreted_args(client_args)
        for index, value in enumerate(args):
            if value.startswith("--resume="):
                identity = value.partition("=")[2]
                return identity or None
            if value.startswith("-r") and value != "-r":
                identity = value[2:].removeprefix("=")
                return identity or None
            if value in {"--resume", "-r"}:
                identity_index = index + 1
                if identity_index < len(args) and not args[identity_index].startswith("-"):
                    return args[identity_index]
                return None
        return None

    def validate_client_args(self, client_args: Sequence[str]) -> None:
        args = self.interpreted_args(client_args)
        resume_count = 0
        for value in args:
            if value in {"--continue", "-c"} or value.startswith("--continue="):
                raise LaunchConflict(
                    "Claude continuation requires an explicit canonical --resume UUID."
                )
            if value == "--session-id" or value.startswith("--session-id="):
                raise LaunchConflict("Claude --session-id is owned by the Mr Hide launcher.")
            if value == "--fork-session" or value.startswith("--fork-session="):
                raise LaunchConflict(
                    "Claude session forks require a launcher-owned canonical identity."
                )
            if (
                value in {"--resume", "-r"}
                or value.startswith("--resume=")
                or (value.startswith("-r") and value != "-r")
            ):
                resume_count += 1
        if resume_count > 1:
            raise LaunchConflict("Claude accepts exactly one explicit resume identity.")
