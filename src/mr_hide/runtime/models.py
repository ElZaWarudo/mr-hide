"""Immutable runtime outcomes and safe lifecycle errors."""

from __future__ import annotations

from dataclasses import dataclass


class SupervisorError(RuntimeError):
    """Base class for safe user-facing supervisor failures."""


class ProxyStartupError(SupervisorError):
    """Raised when the loopback proxy never becomes ready."""


class ProxyRuntimeError(SupervisorError):
    """Raised when the proxy stops before the owned client."""


class ProcessCleanupError(SupervisorError):
    """Raised when an owned process tree cannot be confirmed stopped."""


@dataclass(frozen=True, slots=True)
class SupervisorResult:
    exit_code: int
    endpoint: str
    resume_identity: str | None
