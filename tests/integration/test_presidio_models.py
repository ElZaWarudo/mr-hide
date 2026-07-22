from __future__ import annotations

import pytest
import spacy.util

from mr_hide.privacy.detection import build_local_detector, build_presidio_detector
from mr_hide.privacy.overlap import resolve_overlaps


@pytest.mark.nlp_models
def test_pinned_english_and_spanish_models_detect_mixed_fixture() -> None:
    if not spacy.util.is_package("en_core_web_sm") or not spacy.util.is_package(
        "es_core_news_sm"
    ):
        pytest.skip("pinned English and Spanish spaCy models are not installed")
    text = "Alice vive en Madrid y su correo es alice@example.com"

    detected = build_presidio_detector().detect(text)
    resolved = resolve_overlaps(text, detected)

    assert any(item.entity_type == "EMAIL_ADDRESS" for item in resolved)
    assert {item.language for item in detected} == {"en", "es"}
    assert all(0 <= item.start < item.end <= len(text) for item in resolved)


@pytest.mark.nlp_models
def test_email_validation_uses_packaged_suffix_snapshot_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not spacy.util.is_package("en_core_web_sm") or not spacy.util.is_package(
        "es_core_news_sm"
    ):
        pytest.skip("pinned English and Spanish spaCy models are not installed")

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr("requests.sessions.Session.get", reject_network)

    detected = build_presidio_detector().detect("email alice@example.com")

    assert any(item.entity_type == "EMAIL_ADDRESS" for item in detected)


@pytest.mark.nlp_models
def test_default_local_detector_combines_pii_and_secret_detection() -> None:
    if not spacy.util.is_package("en_core_web_sm") or not spacy.util.is_package(
        "es_core_news_sm"
    ):
        pytest.skip("pinned English and Spanish spaCy models are not installed")
    text = "Alice usa el token sk-abcdefghijklmnopqrstuvwxyz"

    detected = build_local_detector().detect(text)

    assert any(item.entity_type == "API_KEY" for item in detected)
    assert any(item.source == "presidio" for item in detected)
