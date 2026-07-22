from __future__ import annotations

from collections.abc import Sequence

import pytest

from mr_hide.privacy.languages import SUPPORTED_LANGUAGES
from mr_hide.privacy.mapping import MappingTable
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError
from mr_hide.privacy.pipeline import PrivacyTransformer
from mr_hide.privacy.scoring import CharacterScorer


class StaticDetector:
    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]:
        return (DetectedSpan(0, len(text), "PERSON", 0.9, languages[0], "fixture"),)


class FailingDetector:
    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]:
        raise PrivacyProcessingError("detection-failed")


def test_pipeline_composes_detector_and_transformer() -> None:
    result = PrivacyTransformer(StaticDetector(), CharacterScorer()).protect("Alice")

    assert result.text != "Alice"
    assert result.mappings.records[0].original == "Alice"


def test_detector_failure_does_not_mutate_existing_mapping() -> None:
    mappings = MappingTable()

    with pytest.raises(PrivacyProcessingError, match="detection-failed"):
        PrivacyTransformer(FailingDetector(), CharacterScorer()).protect("Alice", mappings)

    assert mappings.records == ()
