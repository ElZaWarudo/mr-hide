"""Declared inference routes mediated by the foundation proxy."""

from __future__ import annotations

from starlette.routing import Route

from mr_hide.proxy.forwarding import forward_request

DECLARED_INFERENCE_ROUTES = (
    "/v1/responses",
    "/v1/messages",
    "/v1/messages/count_tokens",
)


def proxy_routes() -> list[Route]:
    return [
        Route(path, endpoint=forward_request, methods=["POST"])
        for path in DECLARED_INFERENCE_ROUTES
    ]
