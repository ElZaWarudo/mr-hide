"""Owned subprocess-group creation and bounded tree cleanup."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mr_hide.runtime.models import ProcessCleanupError


@dataclass(slots=True)
class OwnedProcess:
    process: asyncio.subprocess.Process


async def start_owned_process(
    argv: Sequence[str],
    environment: Mapping[str, str],
) -> OwnedProcess:
    """Start one shell-free process in a group owned by this launch."""

    if not argv:
        raise ValueError("The owned process argv cannot be empty.")
    if os.name == "nt":
        process = await asyncio.create_subprocess_exec(
            *argv,
            env=dict(environment),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = await asyncio.create_subprocess_exec(
            *argv,
            env=dict(environment),
            start_new_session=True,
        )
    return OwnedProcess(process)


async def terminate_owned_process(owned: OwnedProcess, *, timeout: float) -> None:
    """Gracefully stop, then force-kill, only the process group we created."""

    process = owned.process
    if process.returncode is not None:
        return

    _signal_group(process)
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout)
        return
    except TimeoutError:
        pass

    if os.name == "nt":
        await _taskkill_tree(process.pid)
    else:
        with contextlib.suppress(ProcessLookupError):
            _signal_posix_group(process.pid, "SIGKILL")

    try:
        await asyncio.wait_for(process.wait(), timeout=max(timeout, 1.0))
    except TimeoutError as error:
        raise ProcessCleanupError("The owned client process tree did not stop.") from error


def _signal_group(process: asyncio.subprocess.Process) -> None:
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            _signal_posix_group(process.pid, "SIGTERM")
    except (ProcessLookupError, OSError):
        pass


def _signal_posix_group(pid: int, signal_name: str) -> None:
    kill_group = cast(Callable[[int, int], None], os.__dict__["killpg"])
    group_signal = cast(int, getattr(signal, signal_name))
    kill_group(pid, group_signal)


async def _taskkill_tree(pid: int) -> None:
    system_root = os.environ.get("SYSTEMROOT")
    if not system_root:
        raise ProcessCleanupError("Windows process-tree cleanup is unavailable.")
    taskkill = Path(system_root) / "System32" / "taskkill.exe"
    if not taskkill.is_file():
        raise ProcessCleanupError("Windows process-tree cleanup is unavailable.")
    killer = await asyncio.create_subprocess_exec(
        str(taskkill),
        "/PID",
        str(pid),
        "/T",
        "/F",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await killer.wait()
