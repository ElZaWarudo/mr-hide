"""Shared immutable client-launch contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit


class LaunchConflict(ValueError):
    """Raised when native client inputs compete with launcher-owned settings."""


@dataclass(frozen=True, slots=True)
class LaunchSpec:
    argv: tuple[str, ...]
    client_args: tuple[str, ...]
    env: Mapping[str, str]
    resume_identity: str | None


class ClientAdapter(ABC):
    name: str

    @abstractmethod
    def build_launch_spec(
        self,
        *,
        executable: str,
        endpoint: str,
        client_args: Sequence[str],
        parent_env: Mapping[str, str],
    ) -> LaunchSpec:
        """Build a child-only launch specification."""

    @abstractmethod
    def resume_identity(self, client_args: Sequence[str]) -> str | None:
        """Return only an explicit stable native resume identity."""

    def validate_client_args(self, client_args: Sequence[str]) -> None:
        """Reject native arguments that conflict with launcher-owned settings."""

        return None

    @staticmethod
    def interpreted_args(client_args: Sequence[str]) -> tuple[str, ...]:
        """Return only arguments before the native end-of-options boundary."""

        args = tuple(client_args)
        try:
            return args[: args.index("--")]
        except ValueError:
            return args

    @staticmethod
    def frozen_environment(parent_env: Mapping[str, str]) -> Mapping[str, str]:
        return MappingProxyType(dict(parent_env))

    @staticmethod
    def validate_local_endpoint(endpoint: str) -> None:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.port is None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise LaunchConflict("The launcher endpoint must be an HTTP loopback origin.")
