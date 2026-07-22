"""HTTP header policy for the local forwarding boundary."""

from __future__ import annotations

from collections.abc import Iterable

HeaderPair = tuple[bytes, bytes]

_HOP_BY_HOP = frozenset(
    {
        b"connection",
        b"keep-alive",
        b"proxy-authenticate",
        b"proxy-authorization",
        b"te",
        b"trailer",
        b"transfer-encoding",
        b"upgrade",
    }
)


def _connection_tokens(headers: tuple[HeaderPair, ...]) -> frozenset[bytes]:
    return frozenset(
        token.strip().lower()
        for name, value in headers
        if name.lower() == b"connection"
        for token in value.split(b",")
        if token.strip()
    )


def _filter(headers: Iterable[HeaderPair], *, request: bool) -> tuple[HeaderPair, ...]:
    materialized = tuple(headers)
    excluded = _HOP_BY_HOP | _connection_tokens(materialized)
    if request:
        excluded = excluded | {b"host"}
    return tuple((name, value) for name, value in materialized if name.lower() not in excluded)


def filter_request_headers(headers: Iterable[HeaderPair]) -> tuple[HeaderPair, ...]:
    """Remove transport-owned request headers while preserving order and duplicates."""

    return _filter(headers, request=True)


def filter_response_headers(headers: Iterable[HeaderPair]) -> tuple[HeaderPair, ...]:
    """Remove hop-by-hop response headers while preserving order and duplicates."""

    return _filter(headers, request=False)
