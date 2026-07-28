"""Exclusive IPv4 loopback endpoint reservation."""

from __future__ import annotations

import contextlib
import os
import socket
from dataclasses import dataclass
from typing import cast


@dataclass(slots=True)
class ProxyServerTarget:
    socket: socket.socket
    endpoint: str

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self.socket.close()


def reserve_loopback_target() -> ProxyServerTarget:
    """Bind an ephemeral IPv4 loopback socket and retain ownership."""

    reserved = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            reserved.setsockopt(
                socket.SOL_SOCKET,
                cast(int, socket.__dict__["SO_EXCLUSIVEADDRUSE"]),
                1,
            )
        else:
            reserved.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        reserved.bind(("127.0.0.1", 0))
        host, port = reserved.getsockname()[:2]
        return ProxyServerTarget(reserved, f"http://{host}:{port}")
    except BaseException:
        reserved.close()
        raise
