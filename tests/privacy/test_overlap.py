from __future__ import annotations

import pytest

from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError
from mr_hide.privacy.overlap import resolve_overlaps


def span(start: int, end: int, entity: str, score: float) -> DetectedSpan:
    return DetectedSpan(start, end, entity, score, "en", "fixture")


def test_higher_confidence_span_wins_overlap() -> None:
    text = "Bearer secret-value"

    result = resolve_overlaps(
        text,
        (
            span(0, len(text), "AUTH_HEADER", 0.8),
            span(7, len(text), "ACCESS_TOKEN", 0.95),
        ),
    )

    assert result == (span(7, len(text), "ACCESS_TOKEN", 0.95),)


def test_longer_then_entity_priority_break_ties() -> None:
    text = "abcdef"

    result = resolve_overlaps(
        text,
        (
            span(0, 4, "PERSON", 0.8),
            span(0, 5, "PERSON", 0.8),
            span(0, 5, "PRIVATE_KEY", 0.8),
        ),
    )

    assert result == (span(0, 5, "PRIVATE_KEY", 0.8),)


def test_non_overlapping_spans_return_in_text_order() -> None:
    text = "one two three"

    result = resolve_overlaps(
        text,
        (span(8, 13, "PERSON", 0.8), span(0, 3, "PERSON", 0.8)),
    )

    assert [item.start for item in result] == [0, 8]


def test_out_of_bounds_detection_fails_closed() -> None:
    with pytest.raises(PrivacyProcessingError, match="detection-outside-text"):
        resolve_overlaps("short", (span(0, 8, "PERSON", 0.8),))
