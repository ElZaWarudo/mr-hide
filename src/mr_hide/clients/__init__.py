"""Supported native client adapters."""

from collections.abc import Mapping
from types import MappingProxyType

from mr_hide.clients.base import ClientAdapter, LaunchConflict, LaunchSpec
from mr_hide.clients.claude import ClaudeAdapter
from mr_hide.clients.codex import CodexAdapter

_ADAPTERS: Mapping[str, ClientAdapter] = MappingProxyType(
    {"codex": CodexAdapter(), "claude": ClaudeAdapter()}
)


def get_adapter(name: str) -> ClientAdapter:
    return _ADAPTERS[name]

__all__ = [
    "ClaudeAdapter",
    "ClientAdapter",
    "CodexAdapter",
    "LaunchConflict",
    "LaunchSpec",
    "get_adapter",
]
