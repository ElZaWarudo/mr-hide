from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mr_hide.runtime.socket import reserve_loopback_target
from mr_hide.runtime.supervisor import serve_uvicorn
from tests.fixtures.client_contracts import create_contract_app


@asynccontextmanager
async def contract_upstream(
    captured_bodies: list[bytes] | None = None,
) -> AsyncIterator[str]:
    target = reserve_loopback_target()
    ready = asyncio.Event()
    stop = asyncio.Event()
    task = asyncio.create_task(
        serve_uvicorn(create_contract_app(captured_bodies), target, ready, stop)
    )
    try:
        await asyncio.wait_for(ready.wait(), timeout=5)
        yield target.endpoint
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=5)
        target.close()
