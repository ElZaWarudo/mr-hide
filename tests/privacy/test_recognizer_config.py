from __future__ import annotations

from pathlib import Path

import pytest

from mr_hide.config.recognizers import load_local_recognizers
from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.privacy.recognizers import PatternDetector


def write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_loads_declarative_local_recognizer(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "recognizers.yml",
        """
recognizers:
  - name: employee-id
    entity_type: EMPLOYEE_ID
    pattern: 'EMP-\\d{6}'
    score: 0.85
    languages: [en, es]
    context: [employee, empleado]
""",
    )

    patterns = load_local_recognizers(path)
    result = PatternDetector(patterns).detect("empleado EMP-123456", languages=("es",))

    assert len(result) == 1
    assert result[0].entity_type == "EMPLOYEE_ID"


@pytest.mark.parametrize(
    "body",
    (
        (
            "recognizers:\n  - name: evil\n    entity_type: X_ID\n"
            "    pattern: '(a+)+$'\n    score: 0.8\n"
        ),
        (
            "recognizers:\n  - name: evil\n    entity_type: X_ID\n"
            "    pattern: '(?=x)'\n    score: 0.8\n"
        ),
        "recognizers:\n  - name: evil\n    entity_type: lower\n    pattern: 'x'\n    score: 0.8\n",
        (
            "recognizers:\n  - name: evil\n    entity_type: X_ID\n"
            "    pattern: 'x'\n    score: 0.8\n    callback: run-me\n"
        ),
    ),
)
def test_rejects_unsafe_or_executable_configuration(tmp_path: Path, body: str) -> None:
    path = write_config(tmp_path / "recognizers.yml", body)

    with pytest.raises(PrivacyProcessingError, match="recognizer-config-invalid"):
        load_local_recognizers(path)


def test_duplicate_names_are_rejected(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "recognizers.yml",
        """
recognizers:
  - {name: duplicate, entity_type: FIRST_ID, pattern: 'A-\\d+', score: 0.8}
  - {name: duplicate, entity_type: SECOND_ID, pattern: 'B-\\d+', score: 0.8}
""",
    )

    with pytest.raises(PrivacyProcessingError, match="duplicate-recognizer-name"):
        load_local_recognizers(path)


def test_duplicate_yaml_keys_are_rejected(tmp_path: Path) -> None:
    path = write_config(
        tmp_path / "recognizers.yml",
        """
recognizers:
  - name: first
    name: hidden-second
    entity_type: EMPLOYEE_ID
    pattern: 'EMP-\\d+'
    score: 0.8
""",
    )

    with pytest.raises(PrivacyProcessingError, match="recognizer-config-invalid"):
        load_local_recognizers(path)


def test_oversized_configuration_is_rejected_before_read(tmp_path: Path) -> None:
    path = write_config(tmp_path / "recognizers.yml", "x" * (64 * 1024 + 1))

    with pytest.raises(PrivacyProcessingError, match="recognizer-config-too-large"):
        load_local_recognizers(path)
