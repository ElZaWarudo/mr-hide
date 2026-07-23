"""Supervised local proxy and client process lifecycle."""

from typing import TYPE_CHECKING, Any

from mr_hide.runtime.models import SupervisorError, SupervisorResult

if TYPE_CHECKING:
    from mr_hide.runtime.supervisor import supervise_launch


def __getattr__(name: str) -> Any:
    if name == "supervise_launch":
        from mr_hide.runtime.supervisor import supervise_launch

        return supervise_launch
    raise AttributeError(name)


__all__ = ["SupervisorError", "SupervisorResult", "supervise_launch"]
