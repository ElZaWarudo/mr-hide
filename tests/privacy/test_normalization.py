from __future__ import annotations

from mr_hide.privacy.normalization import normalize_entity


def test_text_identity_is_unicode_whitespace_and_case_normalized() -> None:
    assert normalize_entity("  JUAN\u00a0Pérez ", "PERSON") == "juan pérez"


def test_secrets_remain_case_sensitive() -> None:
    assert normalize_entity("AbC-Secret", "API_KEY") != normalize_entity(
        "abc-secret", "API_KEY"
    )


def test_email_normalizes_only_domain_case() -> None:
    assert normalize_entity("User@EXAMPLE.COM", "EMAIL_ADDRESS") == "User@example.com"


def test_phone_formatting_normalizes_to_stable_identity() -> None:
    assert normalize_entity("+1 (202) 555-0100", "PHONE_NUMBER") == "12025550100"
