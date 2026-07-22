from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from starlette.applications import Starlette

from mr_hide.clients.claude import ClaudeAdapter
from mr_hide.runtime import supervisor as supervisor_module
from mr_hide.runtime.models import ProcessCleanupError, ProxyRuntimeError, ProxyStartupError
from mr_hide.runtime.processes import start_owned_process, terminate_owned_process
from mr_hide.runtime.supervisor import ProxyServerTarget, supervise_launch

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fake_client.py"


@pytest.mark.asyncio
async def test_supervisor_starts_ready_proxy_and_propagates_child_exit(
    tmp_path: Path,
) -> None:
    record = tmp_path / "client.json"
    parent = dict(os.environ)
    original = dict(parent)

    result = await supervise_launch(
        adapter=ClaudeAdapter(),
        executable=sys.executable,
        upstream="http://upstream.test",
        client_args=(
            str(FIXTURE),
            "--runtime-record",
            str(record),
            "--probe-endpoint-env",
            "ANTHROPIC_BASE_URL",
            "--exit-code",
            "7",
        ),
        parent_env=parent,
        startup_timeout=5,
        shutdown_timeout=2,
    )

    captured = json.loads(record.read_text(encoding="utf-8"))
    assert result.exit_code == 7
    assert result.endpoint == captured["endpoint"]
    assert captured["probe_status"] == 404
    assert result.endpoint.startswith("http://127.0.0.1:")
    assert parent == original
    _assert_port_released(result.endpoint)


@pytest.mark.asyncio
async def test_stubborn_process_tree_is_killed_without_touching_control_process(
    tmp_path: Path,
) -> None:
    owned_record = tmp_path / "owned.json"
    control_record = tmp_path / "control.json"
    control = await asyncio.create_subprocess_exec(
        sys.executable,
        str(FIXTURE),
        "--runtime-record",
        str(control_record),
        "--sleep",
        "60",
    )
    owned = await start_owned_process(
        (
            sys.executable,
            str(FIXTURE),
            "--runtime-record",
            str(owned_record),
            "--sleep",
            "60",
            "--spawn-descendant",
            "--ignore-termination",
        ),
        os.environ,
    )
    try:
        await _wait_for_file(owned_record)
        captured = json.loads(owned_record.read_text(encoding="utf-8"))
        descendant_pid = int(captured["descendant_pid"])

        await terminate_owned_process(owned, timeout=0.2)

        assert owned.process.returncode is not None
        await _wait_for_process_exit(descendant_pid)
        assert control.returncode is None
    finally:
        if owned.process.returncode is None:
            await terminate_owned_process(owned, timeout=0.2)
        if control.returncode is None:
            control.terminate()
            await control.wait()


@pytest.mark.asyncio
async def test_proxy_startup_failure_never_launches_child(tmp_path: Path) -> None:
    record = tmp_path / "never-created.json"

    async def fail_startup(
        _app: Starlette,
        _target: ProxyServerTarget,
        _ready: asyncio.Event,
        _stop: asyncio.Event,
    ) -> None:
        raise RuntimeError("startup fixture")

    with pytest.raises(ProxyStartupError, match="failed to start"):
        await supervise_launch(
            adapter=ClaudeAdapter(),
            executable=sys.executable,
            upstream="http://upstream.test",
            client_args=(str(FIXTURE), "--runtime-record", str(record)),
            parent_env=os.environ,
            server_serve=fail_startup,
        )

    assert not record.exists()


@pytest.mark.asyncio
async def test_proxy_runtime_failure_terminates_owned_child(tmp_path: Path) -> None:
    record = tmp_path / "terminated.json"

    async def fail_runtime(
        _app: Starlette,
        _target: ProxyServerTarget,
        ready: asyncio.Event,
        _stop: asyncio.Event,
    ) -> None:
        ready.set()
        await _wait_for_file(record)
        raise RuntimeError("runtime fixture")

    with pytest.raises(ProxyRuntimeError, match="stopped unexpectedly"):
        await supervise_launch(
            adapter=ClaudeAdapter(),
            executable=sys.executable,
            upstream="http://upstream.test",
            client_args=(
                str(FIXTURE),
                "--runtime-record",
                str(record),
                "--sleep",
                "60",
            ),
            parent_env=os.environ,
            shutdown_timeout=0.2,
            server_serve=fail_runtime,
        )

    captured = json.loads(record.read_text(encoding="utf-8"))
    await _wait_for_process_exit(int(captured["pid"]))


@pytest.mark.asyncio
async def test_cleanup_failure_still_releases_proxy_and_socket(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = tmp_path / "cleanup-failure.json"
    real_terminate = supervisor_module.terminate_owned_process

    async def terminate_then_report_failure(
        owned: supervisor_module.OwnedProcess,
        *,
        timeout: float,
    ) -> None:
        await real_terminate(owned, timeout=timeout)
        raise ProcessCleanupError("cleanup fixture")

    monkeypatch.setattr(
        supervisor_module,
        "terminate_owned_process",
        terminate_then_report_failure,
    )

    endpoint: str | None = None

    async def fail_runtime(
        _app: Starlette,
        target: ProxyServerTarget,
        ready: asyncio.Event,
        _stop: asyncio.Event,
    ) -> None:
        nonlocal endpoint
        endpoint = target.endpoint
        ready.set()
        await _wait_for_file(record)
        raise RuntimeError("runtime fixture")

    with pytest.raises(ProcessCleanupError, match="cleanup fixture"):
        await supervise_launch(
            adapter=ClaudeAdapter(),
            executable=sys.executable,
            upstream="http://upstream.test",
            client_args=(
                str(FIXTURE),
                "--runtime-record",
                str(record),
                "--sleep",
                "60",
            ),
            parent_env=os.environ,
            shutdown_timeout=0.2,
            server_serve=fail_runtime,
        )

    captured = json.loads(record.read_text(encoding="utf-8"))
    await _wait_for_process_exit(int(captured["pid"]))
    assert endpoint is not None
    _assert_port_released(endpoint)


@pytest.mark.asyncio
async def test_supervisor_cancellation_releases_child_and_socket(tmp_path: Path) -> None:
    record = tmp_path / "cancelled.json"
    task = asyncio.create_task(
        supervise_launch(
            adapter=ClaudeAdapter(),
            executable=sys.executable,
            upstream="http://upstream.test",
            client_args=(
                str(FIXTURE),
                "--runtime-record",
                str(record),
                "--probe-endpoint-env",
                "ANTHROPIC_BASE_URL",
                "--sleep",
                "60",
                "--ignore-termination",
            ),
            parent_env=os.environ,
            shutdown_timeout=0.2,
        )
    )
    await _wait_for_file(record)
    captured = json.loads(record.read_text(encoding="utf-8"))

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await _wait_for_process_exit(int(captured["pid"]))
    _assert_port_released(str(captured["endpoint"]))


@pytest.mark.asyncio
async def test_cancelling_server_wrapper_does_not_orphan_uvicorn_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    class FakeManagedServer:
        def __init__(self, _config: object, _ready: asyncio.Event) -> None:
            self.should_exit = False

        async def serve(self, *, sockets: list[socket.socket]) -> None:
            assert sockets
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    monkeypatch.setattr(supervisor_module, "_ManagedServer", FakeManagedServer)
    target = supervisor_module.reserve_loopback_target()
    task = asyncio.create_task(
        supervisor_module.serve_uvicorn(
            Starlette(),
            target,
            asyncio.Event(),
            asyncio.Event(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(cancelled.wait(), timeout=1)
    finally:
        target.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows exclusive-bind semantics")
def test_reserved_windows_port_rejects_reuseaddr_competitor() -> None:
    from mr_hide.runtime.socket import reserve_loopback_target

    target = reserve_loopback_target()
    parsed = urlsplit(target.endpoint)
    assert parsed.hostname is not None and parsed.port is not None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as competitor:
            competitor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            with pytest.raises(OSError):
                competitor.bind((parsed.hostname, parsed.port))
    finally:
        target.close()


def _assert_port_released(endpoint: str) -> None:
    parsed = urlsplit(endpoint)
    assert parsed.hostname is not None and parsed.port is not None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((parsed.hostname, parsed.port))


async def _wait_for_file(path: Path, timeout: float = 5) -> None:
    await _wait_until(path.exists, timeout)


async def _wait_for_process_exit(pid: int, timeout: float = 5) -> None:
    await _wait_until(lambda: not _process_exists(pid), timeout)


async def _wait_until(predicate: Callable[[], bool], timeout: float) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.02)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
