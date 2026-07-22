"""Provider-neutral detection, substitution, and restoration primitives."""

from mr_hide.privacy.mapping import (
    MappingRecord,
    MappingTable,
    SubstitutionMode,
    TransformationResult,
    restore_text,
    transform_text,
)
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError

__all__ = [
    "DetectedSpan",
    "MappingRecord",
    "MappingTable",
    "PrivacyProcessingError",
    "SubstitutionMode",
    "TransformationResult",
    "restore_text",
    "transform_text",
]
