"""Codex native-state-preserving adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from mr_hide.clients.base import ClientAdapter, LaunchConflict, LaunchSpec

_CODEX_ENDPOINT_KEYS = ("openai_base_url", "base_url")
_RESUME_OPTIONS_WITH_VALUE = {
    "-c",
    "--config",
    "--enable",
    "--disable",
    "-i",
    "--image",
    "-m",
    "--model",
    "--sandbox",
    "--output-schema",
    "-o",
    "--output-last-message",
}


class CodexAdapter(ClientAdapter):
    name = "codex"

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
        env = self.frozen_environment(parent_env)
        return LaunchSpec(
            argv=(
                executable,
                "--config",
                f'openai_base_url="{endpoint}/v1"',
                *args,
            ),
            client_args=args,
            env=env,
            resume_identity=self.resume_identity(args),
        )

    def resume_identity(self, client_args: Sequence[str]) -> str | None:
        args = self.interpreted_args(client_args)
        for index, value in enumerate(args):
            if value != "resume":
                continue
            candidate_index = index + 1
            while candidate_index < len(args):
                candidate = args[candidate_index]
                if candidate in {"--last", "--"}:
                    return None
                option_name = candidate.partition("=")[0]
                if option_name in _RESUME_OPTIONS_WITH_VALUE:
                    candidate_index += 1 if "=" in candidate else 2
                    continue
                if candidate.startswith("-"):
                    candidate_index += 1
                    continue
                return candidate
            return None
        return None

    def validate_client_args(self, client_args: Sequence[str]) -> None:
        args = self.interpreted_args(client_args)
        for index, value in enumerate(args):
            lowered = value.lower()
            if value in {"--config", "-c"}:
                candidate = args[index + 1].lower() if index + 1 < len(args) else ""
            elif value.startswith("--config="):
                candidate = lowered.partition("=")[2]
            elif value.startswith("-c") and value != "-c":
                candidate = lowered[2:]
            else:
                continue
            if any(key in candidate for key in _CODEX_ENDPOINT_KEYS):
                raise LaunchConflict(
                    "Client arguments conflict with the Mr Hide-owned endpoint configuration."
                )
