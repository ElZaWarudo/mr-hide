from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

import httpx


class TrackedByteStream(httpx.AsyncByteStream):
    def __init__(
        self,
        chunks: tuple[bytes, ...],
        *,
        failure: Exception | None = None,
    ) -> None:
        self.chunks = chunks
        self.failure = failure
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk
        if self.failure is not None:
            raise self.failure

    async def aclose(self) -> None:
        self.closed = True


@dataclass(slots=True)
class CapturedRequest:
    method: str
    url: str
    headers: tuple[tuple[bytes, bytes], ...]
    chunks: tuple[bytes, ...]


@dataclass(slots=True)
class RecordingTransport(httpx.AsyncBaseTransport):
    response_factory: Callable[[httpx.Request], httpx.Response]
    requests: list[CapturedRequest] = field(default_factory=list)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        chunks = tuple([chunk async for chunk in request.stream])
        self.requests.append(
            CapturedRequest(
                method=request.method,
                url=str(request.url),
                headers=tuple(request.headers.raw),
                chunks=chunks,
            )
        )
        return self.response_factory(request)


def client_factory(transport: httpx.AsyncBaseTransport) -> Callable[[], httpx.AsyncClient]:
    return lambda: httpx.AsyncClient(
        transport=transport,
        trust_env=False,
        follow_redirects=False,
    )

