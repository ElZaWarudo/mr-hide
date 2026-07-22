"""Coordinate one proxy server and one owned native client process."""

from __future__ import annotations

import asyncio
import contextlib
import socket
from collections.abc import Awaitable, Callable, Generator, Mapping, Sequence
from typing import cast

import uvicorn
from starlette.applications import Starlette

from mr_hide.clients.base import ClientAdapter
from mr_hide.proxy.app import create_proxy_app
from mr_hide.runtime.models import ProxyRuntimeError, ProxyStartupError, SupervisorResult
from mr_hide.runtime.processes import OwnedProcess, start_owned_process, terminate_owned_process
from mr_hide.runtime.socket import ProxyServerTarget, reserve_loopback_target

ProxyServerServe = Callable[
    [Starlette, ProxyServerTarget, asyncio.Event, asyncio.Event],
    Awaitable[None],
]


class _ManagedServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, ready: asyncio.Event) -> None:
        super().__init__(config)
        self._ready = ready

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None, None, None]:
        yield

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            self._ready.set()


async def serve_uvicorn(
    app: Starlette,
    target: ProxyServerTarget,
    ready: asyncio.Event,
    stop: asyncio.Event,
) -> None:
    """Serve on the reserved socket until the owner requests shutdown."""

    config = uvicorn.Config(
        app,
        access_log=False,
        lifespan="on",
        log_config=None,
        log_level="critical",
    )
    server = _ManagedServer(config, ready)
    server_task = asyncio.create_task(server.serve(sockets=[target.socket]))
    stop_task = asyncio.create_task(stop.wait())
    try:
        done, _pending = await asyncio.wait(
            {server_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done and not server_task.done():
            server.should_exit = True
        await server_task
    finally:
        stop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stop_task


async def supervise_launch(
    *,
    adapter: ClientAdapter,
    executable: str,
    upstream: str,
    client_args: Sequence[str],
    parent_env: Mapping[str, str],
    startup_timeout: float = 10.0,
    shutdown_timeout: float = 5.0,
    server_serve: ProxyServerServe = serve_uvicorn,
) -> SupervisorResult:
    """Run a configured client only while its loopback proxy remains healthy."""

    target = reserve_loopback_target()
    ready = asyncio.Event()
    stop = asyncio.Event()
    server_task: asyncio.Future[None] = asyncio.ensure_future(
        server_serve(create_proxy_app(upstream), target, ready, stop)
    )
    child: OwnedProcess | None = None
    child_wait: asyncio.Task[int] | None = None
    try:
        await _await_server_start(server_task, ready, startup_timeout)
        launch = adapter.build_launch_spec(
            executable=executable,
            endpoint=target.endpoint,
            client_args=client_args,
            parent_env=parent_env,
        )
        child = await start_owned_process(launch.argv, launch.env)
        child_wait = asyncio.create_task(child.process.wait())
        runtime_waiters = {
            cast(asyncio.Future[object], server_task),
            cast(asyncio.Future[object], child_wait),
        }
        done, _pending = await asyncio.wait(
            runtime_waiters,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if server_task in done:
            await asyncio.gather(server_task, return_exceptions=True)
            raise ProxyRuntimeError("The local proxy stopped unexpectedly.")
        return SupervisorResult(
            exit_code=child_wait.result(),
            endpoint=target.endpoint,
            resume_identity=launch.resume_identity,
        )
    finally:
        if child is not None and child.process.returncode is None:
            await terminate_owned_process(child, timeout=shutdown_timeout)
        if child_wait is not None and not child_wait.done():
            child_wait.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await child_wait
        stop.set()
        await _stop_server(server_task, shutdown_timeout)
        target.close()


async def _await_server_start(
    server_task: asyncio.Future[None],
    ready: asyncio.Event,
    timeout: float,
) -> None:
    ready_task = asyncio.create_task(ready.wait())
    try:
        startup_waiters = {
            cast(asyncio.Future[object], server_task),
            cast(asyncio.Future[object], ready_task),
        }
        done, _pending = await asyncio.wait(
            startup_waiters,
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if server_task in done:
            await asyncio.gather(server_task, return_exceptions=True)
            raise ProxyStartupError("The local proxy failed to start.")
        if ready_task not in done:
            raise ProxyStartupError("The local proxy failed to start before the timeout.")
    finally:
        ready_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ready_task


async def _stop_server(server_task: asyncio.Future[None], timeout: float) -> None:
    if server_task.done():
        await asyncio.gather(server_task, return_exceptions=True)
        return
    try:
        await asyncio.wait_for(asyncio.shield(server_task), timeout=max(timeout, 1.0))
    except TimeoutError:
        server_task.cancel()
        await asyncio.gather(server_task, return_exceptions=True)
