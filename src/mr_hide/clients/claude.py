"""Claude Code native-state-preserving adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from mr_hide.clients.base import ClientAdapter, LaunchSpec


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
            if value in {"--resume", "-r"}:
                identity_index = index + 1
                if identity_index < len(args) and not args[identity_index].startswith("-"):
                    return args[identity_index]
                return None
        return None
