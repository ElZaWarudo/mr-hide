"""Fail-closed composition of detection and reversible transformation."""

from __future__ import annotations

from collections.abc import Sequence

from mr_hide.privacy.detection import Detector
from mr_hide.privacy.languages import SUPPORTED_LANGUAGES
from mr_hide.privacy.mapping import (
    MappingTable,
    SubstitutionMode,
    TransformationResult,
    transform_text,
)
from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.privacy.scoring import TokenScorer


class PrivacyTransformer:
    def __init__(self, detector: Detector, scorer: TokenScorer) -> None:
        self._detector = detector
        self._scorer = scorer

    def protect(
        self,
        text: str,
        mappings: MappingTable | None = None,
        *,
        mode: SubstitutionMode = SubstitutionMode.ALIAS,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> TransformationResult:
        try:
            detections = self._detector.detect(text, languages=languages)
        except PrivacyProcessingError:
            raise
        except Exception:
            raise PrivacyProcessingError("detection-failed") from None
        return transform_text(
            text,
            detections,
            mappings,
            mode=mode,
            scorer=self._scorer,
        )
