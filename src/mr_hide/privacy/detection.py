"""Detector ports and the local Presidio adapter."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Protocol

import spacy.util
import tldextract
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import EmailRecognizer

from mr_hide.privacy.languages import SUPPORTED_LANGUAGES
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError

if TYPE_CHECKING:
    from mr_hide.privacy.recognizers import LocalPattern


class Detector(Protocol):
    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]: ...


class AnalyzerResult(Protocol):
    start: int
    end: int
    entity_type: str
    score: float


class AnalyzerPort(Protocol):
    def analyze(self, text: str, language: str) -> Sequence[AnalyzerResult]: ...


class _OfflineEmailRecognizer(EmailRecognizer):
    _extractor = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=())

    def validate_result(self, pattern_text: str) -> bool:
        return self._extractor(pattern_text).fqdn != ""


class PresidioDetector:
    def __init__(self, analyzer: AnalyzerPort) -> None:
        self._analyzer = analyzer

    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]:
        if not text:
            return ()
        if not languages or any(language not in SUPPORTED_LANGUAGES for language in languages):
            raise PrivacyProcessingError("unsupported-detection-language")
        detected: list[DetectedSpan] = []
        try:
            for language in dict.fromkeys(languages):
                for result in self._analyzer.analyze(text=text, language=language):
                    detected.append(
                        DetectedSpan(
                            start=result.start,
                            end=result.end,
                            entity_type=result.entity_type.upper(),
                            score=float(result.score),
                            language=language,
                            source="presidio",
                        )
                    )
        except PrivacyProcessingError:
            raise
        except Exception:
            raise PrivacyProcessingError("detection-failed") from None
        return tuple(detected)


class CompositeDetector:
    def __init__(self, detectors: Iterable[Detector]) -> None:
        self._detectors = tuple(detectors)
        if not self._detectors:
            raise PrivacyProcessingError("detection-unavailable")

    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]:
        detected: list[DetectedSpan] = []
        try:
            for detector in self._detectors:
                detected.extend(detector.detect(text, languages=languages))
        except PrivacyProcessingError:
            raise
        except Exception:
            raise PrivacyProcessingError("detection-failed") from None
        return tuple(detected)


def build_presidio_detector(
    *,
    english_model: str = "en_core_web_sm",
    spanish_model: str = "es_core_news_sm",
) -> PresidioDetector:
    if not spacy.util.is_package(english_model) or not spacy.util.is_package(spanish_model):
        raise PrivacyProcessingError("nlp-model-unavailable")
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "en", "model_name": english_model},
            {"lang_code": "es", "model_name": spanish_model},
        ],
    }
    try:
        engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
        analyzer = AnalyzerEngine(
            nlp_engine=engine,
            supported_languages=list(SUPPORTED_LANGUAGES),
        )
        analyzer.registry.remove_recognizer("EmailRecognizer")
        for language in SUPPORTED_LANGUAGES:
            analyzer.registry.add_recognizer(
                _OfflineEmailRecognizer(supported_language=language)
            )
    except Exception:
        raise PrivacyProcessingError("nlp-model-unavailable") from None
    return PresidioDetector(analyzer)


def build_local_detector(
    *,
    custom_patterns: Sequence[LocalPattern] = (),
    english_model: str = "en_core_web_sm",
    spanish_model: str = "es_core_news_sm",
) -> CompositeDetector:
    from mr_hide.privacy.recognizers import (
        BUILTIN_SECRET_PATTERNS,
        PatternDetector,
    )

    return CompositeDetector(
        (
            build_presidio_detector(
                english_model=english_model,
                spanish_model=spanish_model,
            ),
            PatternDetector((*BUILTIN_SECRET_PATTERNS, *custom_patterns)),
        )
    )
