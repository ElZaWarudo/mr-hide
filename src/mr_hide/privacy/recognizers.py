"""Timeout-bounded local recognizers for technical secrets and identifiers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import regex

from mr_hide.privacy.languages import SUPPORTED_LANGUAGES
from mr_hide.privacy.models import DetectedSpan, PrivacyProcessingError

_MATCH_TIMEOUT_SECONDS = 0.05


@dataclass(frozen=True, slots=True)
class LocalPattern:
    name: str
    entity_type: str
    expression: str
    score: float
    languages: tuple[str, ...] = SUPPORTED_LANGUAGES
    group: str | int = 0
    context: tuple[str, ...] = ()
    ignore_case: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.entity_type or self.entity_type != self.entity_type.upper():
            raise PrivacyProcessingError("invalid-recognizer-metadata")
        if not 0 < self.score <= 1:
            raise PrivacyProcessingError("invalid-recognizer-score")
        if not self.languages or any(item not in SUPPORTED_LANGUAGES for item in self.languages):
            raise PrivacyProcessingError("unsupported-recognizer-language")


BUILTIN_SECRET_PATTERNS: tuple[LocalPattern, ...] = (
    LocalPattern(
        "private-key",
        "PRIVATE_KEY",
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?"
        r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        0.99,
    ),
    LocalPattern(
        "jwt",
        "JWT",
        r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b",
        0.98,
    ),
    LocalPattern(
        "known-api-key",
        "API_KEY",
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|"
        r"glpat-[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,}|"
        r"xox[baprs]-[A-Za-z0-9-]{10,})\b",
        0.98,
    ),
    LocalPattern(
        "bearer-token",
        "ACCESS_TOKEN",
        r"\bBearer\s+(?P<secret>[A-Za-z0-9._~+/-]{12,}=*)",
        0.96,
        group="secret",
        ignore_case=True,
    ),
    LocalPattern(
        "authorization-credential",
        "AUTH_HEADER",
        r"\b(?:Authorization\s*:\s*)?(?:Basic|Token|ApiKey)\s+"
        r"(?P<secret>[A-Za-z0-9._~+/-]{8,}=*)",
        0.96,
        group="secret",
        ignore_case=True,
    ),
    LocalPattern(
        "database-password",
        "DATABASE_CREDENTIAL",
        r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis)://[^\s:/]+:(?P<secret>[^\s@/]+)@",
        0.97,
        group="secret",
        ignore_case=True,
    ),
    LocalPattern(
        "password-assignment",
        "PASSWORD",
        r"\b(?:password|passwd|pwd)\s*[:=]\s*[\"']?(?P<secret>[^\s\"',;]{8,})",
        0.9,
        group="secret",
        ignore_case=True,
    ),
    LocalPattern(
        "generic-secret-assignment",
        "SECRET",
        r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"']?(?P<secret>[A-Za-z0-9._~+/-]{12,}=*)",
        0.9,
        group="secret",
        ignore_case=True,
    ),
)


class PatternDetector:
    def __init__(self, patterns: Sequence[LocalPattern]) -> None:
        self._patterns = tuple(patterns)
        try:
            self._compiled = tuple(
                (
                    pattern,
                    regex.compile(
                        pattern.expression,
                        regex.IGNORECASE if pattern.ignore_case else 0,
                    ),
                )
                for pattern in self._patterns
            )
        except Exception:
            raise PrivacyProcessingError("recognizer-invalid") from None

    def detect(
        self,
        text: str,
        *,
        languages: Sequence[str] = SUPPORTED_LANGUAGES,
    ) -> tuple[DetectedSpan, ...]:
        if not languages or any(language not in SUPPORTED_LANGUAGES for language in languages):
            raise PrivacyProcessingError("unsupported-detection-language")
        detected: list[DetectedSpan] = []
        try:
            for pattern, compiled in self._compiled:
                applicable = tuple(item for item in languages if item in pattern.languages)
                if not applicable:
                    continue
                for match in compiled.finditer(text, timeout=_MATCH_TIMEOUT_SECONDS):
                    start, end = match.span(pattern.group)
                    if start == end or not _context_matches(text, start, end, pattern.context):
                        continue
                    detected.append(
                        DetectedSpan(
                            start,
                            end,
                            pattern.entity_type,
                            pattern.score,
                            applicable[0],
                            pattern.name,
                        )
                    )
        except TimeoutError:
            raise PrivacyProcessingError("recognizer-timeout") from None
        except PrivacyProcessingError:
            raise
        except Exception:
            raise PrivacyProcessingError("recognizer-failed") from None
        return tuple(detected)


def _context_matches(
    text: str,
    start: int,
    end: int,
    context: tuple[str, ...],
) -> bool:
    if not context:
        return True
    window = text[max(0, start - 80) : min(len(text), end + 80)].casefold()
    return any(item.casefold() in window for item in context)


def builtin_secret_detector() -> PatternDetector:
    return PatternDetector(BUILTIN_SECRET_PATTERNS)
