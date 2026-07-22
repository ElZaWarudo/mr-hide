"""Safe domain models for privacy processing."""

from __future__ import annotations

from dataclasses import dataclass


class PrivacyProcessingError(RuntimeError):
    """A redacted, fail-closed privacy processing failure."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class DetectedSpan:
    start: int
    end: int
    entity_type: str
    score: float
    language: str
    source: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise PrivacyProcessingError("invalid-detection-span")
        if not 0 <= self.score <= 1:
            raise PrivacyProcessingError("invalid-detection-score")
        if not self.entity_type or self.entity_type != self.entity_type.upper():
            raise PrivacyProcessingError("invalid-entity-type")
        if not self.language or not self.source:
            raise PrivacyProcessingError("invalid-detection-metadata")

    @property
    def length(self) -> int:
        return self.end - self.start
