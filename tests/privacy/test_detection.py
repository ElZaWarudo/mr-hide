from __future__ import annotations

from dataclasses import dataclass

import pytest

from mr_hide.privacy.detection import CompositeDetector, PresidioDetector, build_presidio_detector
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError


@dataclass
class FakeResult:
    start: int
    end: int
    entity_type: str
    score: float


class FakeAnalyzer:
    def __init__(self, results: dict[str, list[FakeResult]] | None = None) -> None:
        self.results = results or {}
        self.calls: list[tuple[str, str]] = []

    def analyze(self, *, text: str, language: str) -> list[FakeResult]:
        self.calls.append((text, language))
        return self.results.get(language, [])


class FailingAnalyzer:
    def analyze(self, *, text: str, language: str) -> list[FakeResult]:
        raise RuntimeError(f"must-not-leak:{text}:{language}")


class StaticDetector:
    def __init__(self, result: DetectedSpan) -> None:
        self.result = result

    def detect(
        self, text: str, *, languages: tuple[str, ...] = ("en", "es")
    ) -> tuple[DetectedSpan, ...]:
        return (self.result,)


def test_presidio_detector_combines_english_and_spanish_results() -> None:
    analyzer = FakeAnalyzer(
        {
            "en": [FakeResult(0, 5, "person", 0.8)],
            "es": [FakeResult(10, 16, "location", 0.7)],
        }
    )

    result = PresidioDetector(analyzer).detect("Alice viajó Madrid")

    assert [item.entity_type for item in result] == ["PERSON", "LOCATION"]
    assert [item.language for item in result] == ["en", "es"]


def test_detection_failure_is_redacted() -> None:
    with pytest.raises(PrivacyProcessingError, match=r"^detection-failed$") as caught:
        PresidioDetector(FailingAnalyzer()).detect("PERSONAL_SENTINEL")

    assert "PERSONAL_SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_unsupported_language_fails_before_analyzer_call() -> None:
    analyzer = FakeAnalyzer()

    with pytest.raises(PrivacyProcessingError, match="unsupported-detection-language"):
        PresidioDetector(analyzer).detect("text", languages=("fr",))

    assert analyzer.calls == []


def test_composite_detector_preserves_all_detector_evidence() -> None:
    first = DetectedSpan(0, 5, "PERSON", 0.8, "en", "first")
    second = DetectedSpan(0, 5, "API_KEY", 0.9, "en", "second")

    result = CompositeDetector((StaticDetector(first), StaticDetector(second))).detect("Alice")

    assert result == (first, second)


def test_empty_composite_detector_is_rejected() -> None:
    with pytest.raises(PrivacyProcessingError, match="detection-unavailable"):
        CompositeDetector(())


def test_missing_spacy_model_fails_closed_without_model_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("mr_hide.privacy.detection.spacy.util.is_package", lambda _name: False)

    with pytest.raises(PrivacyProcessingError, match=r"^nlp-model-unavailable$") as caught:
        build_presidio_detector(english_model="secret-model-name")

    assert "secret-model-name" not in str(caught.value)
