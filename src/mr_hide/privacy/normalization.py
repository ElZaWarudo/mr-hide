"""Entity-aware lookup normalization which never replaces the stored original."""

from __future__ import annotations

import re
import unicodedata

_SECRET_TYPES = {
    "API_KEY",
    "ACCESS_TOKEN",
    "AUTH_HEADER",
    "DATABASE_CREDENTIAL",
    "JWT",
    "PASSWORD",
    "PRIVATE_KEY",
    "SECRET",
}
_DIGIT_TYPES = {"CREDIT_CARD", "IBAN_CODE", "PHONE_NUMBER"}


def normalize_entity(value: str, entity_type: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    if entity_type in _SECRET_TYPES:
        return normalized
    if entity_type in _DIGIT_TYPES:
        compact = "".join(character for character in normalized if character.isalnum())
        return compact.casefold()
    if entity_type == "EMAIL_ADDRESS" and "@" in normalized:
        local, domain = normalized.rsplit("@", 1)
        return f"{local}@{domain.casefold()}"
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def entity_family(entity_type: str) -> str:
    if entity_type in _SECRET_TYPES:
        return "SECRET"
    families = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "PHONE",
        "CREDIT_CARD": "CARD",
        "IP_ADDRESS": "IP",
        "LOCATION": "LOCATION",
        "PERSON": "PERSON",
        "ORGANIZATION": "ORGANIZATION",
        "MEDICAL_LICENSE": "MEDICAL",
    }
    return families.get(entity_type, "VALUE")
