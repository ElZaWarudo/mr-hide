from __future__ import annotations

import pytest

from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.privacy.recognizers import LocalPattern, PatternDetector, builtin_secret_detector


@pytest.mark.parametrize(
    ("text", "expected", "entity_type"),
    (
        ("token sk-abcdefghijklmnopqrstuvwxyz", "sk-abcdefghijklmnopqrstuvwxyz", "API_KEY"),
        (
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz.123",
            "abcdefghijklmnopqrstuvwxyz.123",
            "ACCESS_TOKEN",
        ),
        ("password = 'correct-horse-battery'", "correct-horse-battery", "PASSWORD"),
        (
            "postgresql://user:database-password@example.test/db",
            "database-password",
            "DATABASE_CREDENTIAL",
        ),
        ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpwYXNzd29yZA==", "AUTH_HEADER"),
        ("AWS key AKIAIOSFODNN7EXAMPLE", "AKIAIOSFODNN7EXAMPLE", "API_KEY"),
    ),
)
def test_builtin_secret_detector_returns_only_credential_span(
    text: str,
    expected: str,
    entity_type: str,
) -> None:
    result = builtin_secret_detector().detect(text)
    matching = [item for item in result if item.entity_type == entity_type]

    assert len(matching) == 1
    assert text[matching[0].start : matching[0].end] == expected


def test_private_key_block_is_detected_as_one_span() -> None:
    text = "before\n-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----\nafter"

    result = builtin_secret_detector().detect(text)

    assert len(result) == 1
    assert result[0].entity_type == "PRIVATE_KEY"
    assert text[result[0].start : result[0].end].startswith("-----BEGIN")


def test_context_restricts_custom_identifier_match() -> None:
    detector = PatternDetector(
        (
            LocalPattern(
                "employee-id",
                "EMPLOYEE_ID",
                r"EMP-\d{6}",
                0.8,
                context=("employee", "empleado"),
            ),
        )
    )

    assert detector.detect("employee EMP-123456")
    assert detector.detect("unrelated EMP-123456") == ()


def test_invalid_pattern_metadata_is_rejected() -> None:
    with pytest.raises(PrivacyProcessingError, match="invalid-recognizer-metadata"):
        LocalPattern("name", "person", "value", 0.8)
