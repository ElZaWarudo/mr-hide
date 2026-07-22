"""Constrained YAML configuration for local pattern recognizers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode

from mr_hide.privacy.models import PrivacyProcessingError
from mr_hide.privacy.recognizers import LocalPattern

_MAX_FILE_BYTES = 64 * 1024
_MAX_RECOGNIZERS = 50
_MAX_PATTERN_LENGTH = 512
_ENTITY = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_UNSAFE = re.compile(r"\(\?|\\[1-9]|\(.*[*+]\)[*+{]", re.DOTALL)
_ALLOWED_KEYS = {
    "name",
    "entity_type",
    "pattern",
    "score",
    "languages",
    "context",
    "ignore_case",
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: yaml.SafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise PrivacyProcessingError("recognizer-config-invalid")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_local_recognizers(path: Path) -> tuple[LocalPattern, ...]:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            raise PrivacyProcessingError("recognizer-config-too-large")
        document: object = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=_UniqueKeyLoader,
        )
    except PrivacyProcessingError:
        raise
    except Exception:
        raise PrivacyProcessingError("recognizer-config-invalid") from None
    if not isinstance(document, dict) or set(document) != {"recognizers"}:
        raise PrivacyProcessingError("recognizer-config-invalid")
    raw_items = document["recognizers"]
    if not isinstance(raw_items, list) or len(raw_items) > _MAX_RECOGNIZERS:
        raise PrivacyProcessingError("recognizer-config-invalid")
    patterns = tuple(_parse_pattern(item) for item in raw_items)
    if len({item.name for item in patterns}) != len(patterns):
        raise PrivacyProcessingError("duplicate-recognizer-name")
    return patterns


def _parse_pattern(raw: object) -> LocalPattern:
    if not isinstance(raw, dict) or not set(raw).issubset(_ALLOWED_KEYS):
        raise PrivacyProcessingError("recognizer-config-invalid")
    item: dict[str, Any] = raw
    name = item.get("name")
    entity_type = item.get("entity_type")
    expression = item.get("pattern")
    score = item.get("score")
    languages = item.get("languages", ["en", "es"])
    context = item.get("context", [])
    ignore_case = item.get("ignore_case", False)
    if (
        not isinstance(name, str)
        or not isinstance(entity_type, str)
        or _ENTITY.fullmatch(entity_type) is None
        or not isinstance(expression, str)
        or not expression
        or len(expression) > _MAX_PATTERN_LENGTH
        or _UNSAFE.search(expression)
        or not isinstance(score, int | float)
        or isinstance(score, bool)
        or not isinstance(languages, list)
        or not all(isinstance(value, str) for value in languages)
        or not isinstance(context, list)
        or not all(isinstance(value, str) and len(value) <= 80 for value in context)
        or not isinstance(ignore_case, bool)
    ):
        raise PrivacyProcessingError("recognizer-config-invalid")
    try:
        re.compile(expression)
    except Exception:
        raise PrivacyProcessingError("recognizer-config-invalid") from None
    return LocalPattern(
        name=name,
        entity_type=entity_type,
        expression=expression,
        score=float(score),
        languages=tuple(languages),
        context=tuple(context),
        ignore_case=ignore_case,
    )
