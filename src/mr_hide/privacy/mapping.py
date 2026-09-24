"""Immutable reversible mapping allocation and text transformation."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum

from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError
from mr_hide.privacy.normalization import entity_family, normalize_entity
from mr_hide.privacy.overlap import resolve_overlaps
from mr_hide.privacy.scoring import CharacterScorer, TokenScorer


class SubstitutionMode(StrEnum):
    ALIAS = "alias"
    COMPATIBILITY = "compatibility"


@dataclass(frozen=True, slots=True)
class MappingRecord:
    entity_type: str
    normalized: str
    original: str
    substitute: str
    mode: SubstitutionMode


@dataclass(frozen=True, slots=True)
class MappingTable:
    records: tuple[MappingRecord, ...] = ()

    def __post_init__(self) -> None:
        keys = {(item.entity_type, item.normalized) for item in self.records}
        substitutes = {item.substitute for item in self.records}
        if len(keys) != len(self.records) or len(substitutes) != len(self.records):
            raise PrivacyProcessingError("ambiguous-mapping-state")
        modes = {item.mode for item in self.records}
        if len(modes) > 1:
            raise PrivacyProcessingError("mixed-mapping-modes")
        for item in self.records:
            if (
                not item.original
                or not item.normalized
                or not item.substitute
                or item.entity_type != item.entity_type.upper()
                or not isinstance(item.mode, SubstitutionMode)
                or normalize_entity(item.original, item.entity_type) != item.normalized
                or item.original == item.substitute
            ):
                raise PrivacyProcessingError("invalid-mapping-state")
            other_substitutes = substitutes - {item.substitute}
            if any(
                value in item.substitute
                or value in item.original
                or item.substitute in value
                for value in other_substitutes
            ):
                raise PrivacyProcessingError("nested-mapping-state")

    def find(self, entity_type: str, normalized: str) -> MappingRecord | None:
        return next(
            (
                item
                for item in self.records
                if item.entity_type == entity_type and item.normalized == normalized
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class TransformationResult:
    text: str
    mappings: MappingTable
    replacements: int
    cost_metric: str
    original_cost: int
    substitute_cost: int

    @property
    def claimed_savings(self) -> int:
        return max(0, self.original_cost - self.substitute_cost)


_FAMILY_CODES = {
    "PERSON": "P",
    "EMAIL": "E",
    "PHONE": "T",
    "CARD": "C",
    "IP": "I",
    "LOCATION": "L",
    "ORGANIZATION": "O",
    "MEDICAL": "M",
    "SECRET": "S",
    "VALUE": "V",
}

_SURROGATES: dict[str, tuple[str, ...]] = {
    "PERSON": ("Alex Morgan", "Taylor Reed", "Jordan Blake", "Casey Quinn"),
    "EMAIL": (
        "alex.morgan@example.invalid",
        "taylor.reed@example.invalid",
        "jordan.blake@example.invalid",
    ),
    "PHONE": ("+1 202-555-0100", "+1 202-555-0101", "+1 202-555-0102"),
    "CARD": ("4111 1111 1111 1111", "5555 5555 5555 4444"),
    "IP": ("192.0.2.1", "192.0.2.2", "192.0.2.3"),
    "LOCATION": ("Example City", "Sample Harbor", "Demo Valley"),
    "ORGANIZATION": ("Example Organization", "Sample Cooperative", "Demo Works"),
    "MEDICAL": ("TEST-MEDICAL-0001", "TEST-MEDICAL-0002"),
    "SECRET": ("INVALID_SECRET_0001", "INVALID_SECRET_0002", "INVALID_SECRET_0003"),
    "VALUE": ("Example Value 1", "Example Value 2", "Example Value 3"),
}
_MAX_ALLOCATION_ATTEMPTS = 256


def _candidate_aliases(family: str, index: int) -> tuple[str, ...]:
    code = _FAMILY_CODES[family]
    return (f"<{code}{index}>", f"[{code}{index}]", f"⟦{code}{index}⟧")


def _allocate_alias(
    family: str,
    index: int,
    forbidden: set[str],
    scorer: TokenScorer,
) -> str:
    candidate_index = index
    for _attempt in range(_MAX_ALLOCATION_ATTEMPTS):
        available = [
            item
            for item in _candidate_aliases(family, candidate_index)
            if not _collides(item, forbidden)
        ]
        if available:
            return min(
                available,
                key=lambda item: (_safe_cost(scorer, item), len(item), item),
            )
        candidate_index += 1
    raise PrivacyProcessingError("substitute-space-exhausted")


def _safe_cost(scorer: TokenScorer, value: str) -> int:
    try:
        cost = scorer.cost(value)
    except Exception:
        raise PrivacyProcessingError("token-scoring-failed") from None
    if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
        raise PrivacyProcessingError("token-scoring-failed")
    return cost


def _safe_metric(scorer: TokenScorer) -> str:
    try:
        metric = scorer.metric
    except Exception:
        raise PrivacyProcessingError("token-scoring-failed") from None
    if not isinstance(metric, str) or not metric or len(metric) > 100:
        raise PrivacyProcessingError("token-scoring-failed")
    return metric


def _allocate_surrogate(family: str, index: int, forbidden: set[str]) -> str:
    candidate_index = index
    for _attempt in range(_MAX_ALLOCATION_ATTEMPTS):
        candidate = _surrogate_candidate(family, candidate_index)
        if not _collides(candidate, forbidden):
            return candidate
        candidate_index += 1
    raise PrivacyProcessingError("substitute-space-exhausted")


def _surrogate_candidate(family: str, index: int) -> str:
    bank = _SURROGATES[family]
    if index < len(bank):
        candidate = bank[index]
    elif family == "SECRET":
        candidate = f"INVALID_SECRET_{index + 1:04d}"
    elif family == "EMAIL":
        candidate = f"example.person{index + 1}@example.invalid"
    elif family == "PHONE":
        candidate = f"+1 202-555-{100 + index:04d}"
    elif family == "IP":
        documentation_prefix = int(ipaddress.IPv6Address("2001:db8::"))
        candidate = str(ipaddress.IPv6Address(documentation_prefix + index + 1))
    elif family == "CARD":
        candidate = _test_card_number(index)
    else:
        candidate = f"Example {family.title()} {index + 1}"
    return candidate


def _collides(candidate: str, forbidden: set[str]) -> bool:
    return any(
        value and (candidate in value or value in candidate)
        for value in forbidden
    )


def _test_card_number(index: int) -> str:
    body = f"424242{index:09d}"[-15:]
    digits = [int(value) for value in body]
    total = 0
    for position, digit in enumerate(digits):
        adjusted = digit * 2 if position % 2 == 0 else digit
        total += adjusted - 9 if adjusted > 9 else adjusted
    check = (10 - total % 10) % 10
    number = f"{body}{check}"
    return " ".join(number[offset : offset + 4] for offset in range(0, 16, 4))


def _next_substitute(
    table: MappingTable,
    entity_type: str,
    mode: SubstitutionMode,
    forbidden: set[str],
    scorer: TokenScorer,
) -> str:
    family = entity_family(entity_type)
    used = sum(
        1
        for item in table.records
        if entity_family(item.entity_type) == family and item.mode is mode
    )
    if mode is SubstitutionMode.ALIAS:
        return _allocate_alias(family, used, forbidden, scorer)
    return _allocate_surrogate(family, used, forbidden)


def transform_text(
    text: str,
    detections: tuple[DetectedSpan, ...],
    mappings: MappingTable | None = None,
    *,
    mode: SubstitutionMode = SubstitutionMode.ALIAS,
    scorer: TokenScorer | None = None,
) -> TransformationResult:
    active_scorer = scorer or CharacterScorer()
    working = mappings or MappingTable()
    if any(item.substitute in text for item in working.records):
        raise PrivacyProcessingError("ambiguous-existing-substitute")
    known_spans = list(_known_original_spans(text, working))
    validated_detections = resolve_overlaps(text, detections)
    new_spans: list[DetectedSpan] = []
    for span in validated_detections:
        overlapping = [
            known
            for known in known_spans
            if span.start < known.end and known.start < span.end
        ]
        if not overlapping:
            new_spans.append(span)
        elif all(span.start <= known.start and known.end <= span.end for known in overlapping):
            if any(span.start < known.start or known.end < span.end for known in overlapping):
                known_spans = [known for known in known_spans if known not in overlapping]
                new_spans.append(span)
        elif not all(known.start <= span.start and span.end <= known.end for known in overlapping):
            raise PrivacyProcessingError("ambiguous-known-overlap")
    spans = resolve_overlaps(text, (*known_spans, *new_spans))
    replacements: list[tuple[DetectedSpan, MappingRecord]] = []
    forbidden = {
        text,
        *(item.original for item in working.records),
        *(item.substitute for item in working.records),
    }
    for span in spans:
        original = text[span.start : span.end]
        normalized = normalize_entity(original, span.entity_type)
        if not normalized:
            raise PrivacyProcessingError("empty-normalized-entity")
        record = working.find(span.entity_type, normalized)
        if record is None:
            substitute = _next_substitute(
                working,
                span.entity_type,
                mode,
                forbidden,
                active_scorer,
            )
            record = MappingRecord(
                entity_type=span.entity_type,
                normalized=normalized,
                original=original,
                substitute=substitute,
                mode=mode,
            )
            working = MappingTable((*working.records, record))
            forbidden.add(original)
            forbidden.add(substitute)
        elif record.mode is not mode:
            raise PrivacyProcessingError("mapping-mode-mismatch")
        replacements.append((span, record))

    transformed = text
    for span, record in reversed(replacements):
        transformed = transformed[: span.start] + record.substitute + transformed[span.end :]
    return TransformationResult(
        text=transformed,
        mappings=working,
        replacements=len(replacements),
        cost_metric=_safe_metric(active_scorer),
        original_cost=sum(_safe_cost(active_scorer, text[item.start : item.end]) for item in spans),
        substitute_cost=sum(_safe_cost(active_scorer, item.substitute) for _, item in replacements),
    )


def _known_original_spans(text: str, mappings: MappingTable) -> tuple[DetectedSpan, ...]:
    candidates = sorted(mappings.records, key=lambda item: -len(item.original))
    selected: list[DetectedSpan] = []
    for record in candidates:
        if record.entity_type == "EMAIL_ADDRESS" and "@" in record.original:
            local, domain = record.original.rsplit("@", 1)
            pattern = re.compile(re.escape(local) + r"@(?i:" + re.escape(domain) + r")")
        elif record.entity_type in {
            "API_KEY", "ACCESS_TOKEN", "AUTH_HEADER", "DATABASE_CREDENTIAL", "JWT",
            "PASSWORD", "PRIVATE_KEY", "SECRET", "PHONE_NUMBER",
            "CREDIT_CARD", "IBAN_CODE",
        }:
            pattern = re.compile(re.escape(record.original))
        else:
            parts = re.split(r"\s+", record.original.strip())
            pattern = re.compile(r"\s+".join(re.escape(part) for part in parts), re.IGNORECASE)
        for match in pattern.finditer(text):
            if normalize_entity(match.group(0), record.entity_type) != record.normalized:
                continue
            if any(match.start() < span.end and span.start < match.end() for span in selected):
                continue
            selected.append(
                DetectedSpan(
                    match.start(), match.end(), record.entity_type, 1.0, "en", "known-mapping"
                )
            )
    return tuple(selected)


def restore_text(text: str, mappings: MappingTable) -> str:
    if not mappings.records:
        if _RESERVED_ALIAS.search(text):
            raise PrivacyProcessingError("unknown-substitute")
        return text
    reverse = {item.substitute: item.original for item in mappings.records}
    unknown_aliases = {
        match.group(0)
        for match in _RESERVED_ALIAS.finditer(text)
        if match.group(0) not in reverse
    }
    if unknown_aliases:
        raise PrivacyProcessingError("unknown-substitute")
    pattern = re.compile(
        "|".join(re.escape(item) for item in sorted(reverse, key=len, reverse=True))
    )
    return pattern.sub(lambda match: reverse[match.group(0)], text)


_RESERVED_ALIAS = re.compile(r"(?:<[A-Z][0-9]+>|\[[A-Z][0-9]+\]|⟦[A-Z][0-9]+⟧)")
