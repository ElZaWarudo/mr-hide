"""Supervised local proxy and client process lifecycle."""

from mr_hide.runtime.models import SupervisorError, SupervisorResult
from mr_hide.runtime.supervisor import supervise_launch

__all__ = ["SupervisorError", "SupervisorResult", "supervise_launch"]
