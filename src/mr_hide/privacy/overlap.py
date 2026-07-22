"""Deterministic overlap resolution for detector output."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError

DEFAULT_PRIORITY: dict[str, int] = {
    "PRIVATE_KEY": 100,
    "DATABASE_CREDENTIAL": 95,
    "AUTH_HEADER": 90,
    "ACCESS_TOKEN": 85,
    "API_KEY": 80,
    "JWT": 75,
    "PASSWORD": 70,
}


def resolve_overlaps(
    text: str,
    spans: Iterable[DetectedSpan],
    *,
    priority: Mapping[str, int] = DEFAULT_PRIORITY,
) -> tuple[DetectedSpan, ...]:
    candidates = tuple(spans)
    if any(span.end > len(text) for span in candidates):
        raise PrivacyProcessingError("detection-outside-text")
    ranked = sorted(
        candidates,
        key=lambda span: (
            -span.score,
            -span.length,
            -priority.get(span.entity_type, 0),
            span.start,
            span.end,
            span.entity_type,
        ),
    )
    accepted: list[DetectedSpan] = []
    for candidate in ranked:
        if any(
            candidate.start < current.end and current.start < candidate.end
            for current in accepted
        ):
            continue
        accepted.append(candidate)
    return tuple(sorted(accepted, key=lambda span: (span.start, span.end)))
