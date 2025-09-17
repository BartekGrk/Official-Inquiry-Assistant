"""Utilities for detecting and redacting personally identifiable information (PII)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.config import settings

# Basic regex patterns for the MVP.
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b(?:\+?48)?[\s-]?(?:\d{3}[\s-]?){3}\b")
PESEL_PATTERN = re.compile(r"\b\d{11}\b")
ADDRESS_PATTERN = re.compile(r"ul\.\s*[A-ZĄĆĘŁŃÓŚŹŻ][\w\s\.\-]{3,}")

PII_PATTERNS: Iterable[re.Pattern[str]] = (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    PESEL_PATTERN,
    ADDRESS_PATTERN,
)


@dataclass
class PiiDetectionResult:
    """Result of PII detection."""

    redacted_text: str
    detected: bool


def redact_pii(text: str) -> PiiDetectionResult:
    """Redact PII occurrences in ``text`` using configured placeholder."""

    detected = False
    redacted_text = text
    for pattern in PII_PATTERNS:
        if pattern.search(redacted_text):
            detected = True
            redacted_text = pattern.sub(settings.redact_placeholder, redacted_text)
    return PiiDetectionResult(redacted_text=redacted_text, detected=detected)
