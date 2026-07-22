"""Deterministic synthetic alias cost and collision benchmark."""

from __future__ import annotations

import argparse
import json

from mr_hide.privacy.mapping import restore_text, transform_text
from mr_hide.privacy.models import DetectedSpan

_VALUES = (
    ("PERSON", "Synthetic Example Person"),
    ("EMAIL_ADDRESS", "synthetic.person@example.invalid"),
    ("API_KEY", "sk-synthetic-nonworking-000000000000000000"),
)


def benchmark() -> dict[str, int | str]:
    fragments = [value for _ in range(4) for _entity, value in _VALUES]
    text = " | ".join(fragments)
    detections: list[DetectedSpan] = []
    cursor = 0
    for fragment in fragments:
        start = text.index(fragment, cursor)
        entity_type = next(entity for entity, value in _VALUES if value == fragment)
        detections.append(
            DetectedSpan(start, start + len(fragment), entity_type, 1.0, "en", "synthetic")
        )
        cursor = start + len(fragment)

    result = transform_text(text, tuple(detections))
    if restore_text(result.text, result.mappings) != text:
        raise RuntimeError("benchmark-round-trip-failed")
    if any(value in result.text for _entity, value in _VALUES):
        raise RuntimeError("benchmark-plaintext-leak")
    return {
        "schema_version": 1,
        "metric": result.cost_metric,
        "entities": len(result.mappings.records),
        "occurrences": result.replacements,
        "original_cost": result.original_cost,
        "substitute_cost": result.substitute_cost,
        "claimed_savings": result.claimed_savings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    report = benchmark()
    savings = report["claimed_savings"]
    if arguments.check and (not isinstance(savings, int) or savings <= 0):
        raise SystemExit("benchmark aliases did not reduce the declared metric")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
