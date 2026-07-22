from __future__ import annotations

import pytest

from mr_hide.privacy.mapping import (
    MappingRecord,
    MappingTable,
    SubstitutionMode,
    restore_text,
    transform_text,
)
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError


def detected(text: str, value: str, entity: str = "PERSON") -> DetectedSpan:
    start = text.index(value)
    return DetectedSpan(start, start + len(value), entity, 0.9, "en", "fixture")


def test_repeated_entity_uses_one_mapping_and_round_trips() -> None:
    text = "Alice met Alice"
    first = detected(text, "Alice")
    second_start = text.rindex("Alice")
    second = DetectedSpan(second_start, len(text), "PERSON", 0.9, "en", "fixture")

    result = transform_text(text, (first, second))

    assert len(result.mappings.records) == 1
    substitute = result.mappings.records[0].substitute
    assert result.text == f"{substitute} met {substitute}"
    assert restore_text(result.text, result.mappings) == text


def test_normalized_variant_reuses_first_seen_canonical_original() -> None:
    first = transform_text("Alice", (detected("Alice", "Alice"),))
    second = transform_text("ALICE", (detected("ALICE", "ALICE"),), first.mappings)

    assert len(second.mappings.records) == 1
    assert restore_text(second.text, second.mappings) == "Alice"


def test_distinct_people_receive_sequential_substitutes() -> None:
    text = "Alice and Bob"
    result = transform_text(
        text,
        (detected(text, "Alice"), detected(text, "Bob")),
    )

    assert len({item.substitute for item in result.mappings.records}) == 2


def test_alias_allocator_skips_candidate_present_in_source() -> None:
    text = "<P0> [P0] ⟦P0⟧ Alice"
    result = transform_text(text, (detected(text, "Alice"),))

    assert result.mappings.records[0].substitute in {"<P1>", "[P1]", "⟦P1⟧"}
    assert text.removesuffix("Alice") in result.text


def test_surrogate_allocator_skips_multiple_values_present_in_source() -> None:
    text = "Alex Morgan, Taylor Reed, Jordan Blake, and Alice"
    result = transform_text(
        text,
        (detected(text, "Alice"),),
        mode=SubstitutionMode.COMPATIBILITY,
    )

    assert result.mappings.records[0].substitute == "Casey Quinn"


def test_alias_collision_scan_fails_closed_on_adversarial_exhaustion() -> None:
    occupied = " ".join(
        candidate
        for index in range(300)
        for candidate in (f"<P{index}>", f"[P{index}]", f"⟦P{index}⟧")
    )
    text = f"{occupied} Alice"

    with pytest.raises(PrivacyProcessingError, match="substitute-space-exhausted"):
        transform_text(text, (detected(text, "Alice"),))


def test_existing_substitute_in_new_raw_text_is_ambiguous() -> None:
    first = transform_text("Alice", (detected("Alice", "Alice"),))

    with pytest.raises(PrivacyProcessingError, match="ambiguous-existing-substitute"):
        transform_text(first.text, (), first.mappings)


def test_compatibility_mode_uses_stable_realistic_surrogates() -> None:
    text = "Alice emails alice@example.com"
    result = transform_text(
        text,
        (
            detected(text, "Alice"),
            detected(text, "alice@example.com", "EMAIL_ADDRESS"),
        ),
        mode=SubstitutionMode.COMPATIBILITY,
    )

    assert "Alex Morgan" in result.text
    assert "@example.invalid" in result.text
    assert restore_text(result.text, result.mappings) == text


def test_secret_compatibility_standin_is_explicitly_invalid() -> None:
    text = "token sk-secret-value"
    result = transform_text(
        text,
        (detected(text, "sk-secret-value", "API_KEY"),),
        mode=SubstitutionMode.COMPATIBILITY,
    )

    assert "INVALID_SECRET" in result.text


def test_mapping_mode_cannot_change_within_conversation() -> None:
    first = transform_text("Alice", (detected("Alice", "Alice"),))

    with pytest.raises(PrivacyProcessingError, match="mapping-mode-mismatch"):
        transform_text(
            "ALICE",
            (detected("ALICE", "ALICE"),),
            first.mappings,
            mode=SubstitutionMode.COMPATIBILITY,
        )


def test_mapping_table_rejects_duplicate_substitutes() -> None:
    records = (
        MappingRecord("PERSON", "alice", "Alice", "<P0>", SubstitutionMode.ALIAS),
        MappingRecord("PERSON", "bob", "Bob", "<P0>", SubstitutionMode.ALIAS),
    )

    with pytest.raises(PrivacyProcessingError, match="ambiguous-mapping-state"):
        MappingTable(records)


def test_mapping_table_rejects_original_containing_another_substitute() -> None:
    records = (
        MappingRecord(
            "PERSON",
            "alice <e0>",
            "Alice <E0>",
            "<P0>",
            SubstitutionMode.ALIAS,
        ),
        MappingRecord(
            "EMAIL_ADDRESS",
            "a@example.com",
            "a@example.com",
            "<E0>",
            SubstitutionMode.ALIAS,
        ),
    )

    with pytest.raises(PrivacyProcessingError, match="nested-mapping-state"):
        MappingTable(records)


def test_savings_are_never_claimed_when_substitute_costs_more() -> None:
    result = transform_text("Al", (detected("Al", "Al"),))

    assert result.claimed_savings == 0


def test_compatibility_card_bank_extends_with_valid_unique_test_values() -> None:
    mappings = MappingTable()
    substitutes: list[str] = []
    for index in range(5):
        value = f"4111 1111 1111 {index:04d}"
        result = transform_text(
            value,
            (detected(value, value, "CREDIT_CARD"),),
            mappings,
            mode=SubstitutionMode.COMPATIBILITY,
        )
        mappings = result.mappings
        substitute = result.mappings.records[-1].substitute
        substitutes.append(substitute)
        digits = [int(item) for item in substitute if item.isdigit()]
        checksum = sum(
            (digit * 2 - 9 if digit * 2 > 9 else digit * 2)
            if position % 2 == 0
            else digit
            for position, digit in enumerate(digits)
        )
        assert checksum % 10 == 0

    assert len(set(substitutes)) == 5


def test_unknown_reserved_alias_blocks_restoration() -> None:
    with pytest.raises(PrivacyProcessingError, match="unknown-substitute"):
        restore_text("model invented <P999>", MappingTable())


def test_mapping_table_rejects_mixed_modes() -> None:
    records = (
        MappingRecord("PERSON", "alice", "Alice", "<P0>", SubstitutionMode.ALIAS),
        MappingRecord(
            "PERSON",
            "bob",
            "Bob",
            "Alex Morgan",
            SubstitutionMode.COMPATIBILITY,
        ),
    )

    with pytest.raises(PrivacyProcessingError, match="mixed-mapping-modes"):
        MappingTable(records)


def test_mapping_table_rejects_normalization_mismatch() -> None:
    with pytest.raises(PrivacyProcessingError, match="invalid-mapping-state"):
        MappingTable(
            (
                MappingRecord(
                    "PERSON",
                    "not-alice",
                    "Alice",
                    "<P0>",
                    SubstitutionMode.ALIAS,
                ),
            )
        )


def test_scorer_failure_is_redacted_and_does_not_return_partial_state() -> None:
    class FailingScorer:
        metric = "fixture-tokens"

        def cost(self, value: str) -> int:
            raise RuntimeError(f"scorer-leak:{value}")

    with pytest.raises(PrivacyProcessingError, match="token-scoring-failed") as caught:
        transform_text(
            "PRIVATE_SENTINEL",
            (detected("PRIVATE_SENTINEL", "PRIVATE_SENTINEL"),),
            scorer=FailingScorer(),
        )

    assert "PRIVATE_SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None


def test_default_cost_report_names_its_non_token_metric() -> None:
    result = transform_text("Alice", (detected("Alice", "Alice"),))

    assert result.cost_metric == "utf8-bytes"
