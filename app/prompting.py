"""Prompt construction utilities for the draft generation pipeline."""
from __future__ import annotations

import json
from typing import Dict, Iterable, List, Tuple

from app.schemas import ContextFragment, GenerateDraftRequest
from app.utils.pii import PiiDetectionResult, redact_pii

SYSTEM_RULES = [
    "You are GovLetter, an assistant generating drafts of Polish administrative letters.",
    "Use only the provided legal fragments. Do not rely on outside knowledge.",
    "Each important factual or legal claim must have at least one citation.",
    "Always include a legal_basis section referencing binding law.",
    "List missing information in required_clarifications if needed.",
    "Use formal Polish administrative tone.",
    "Respect conversation history to avoid duplicate drafts.",
    "Respond strictly in valid JSON following the provided schema.",
]


def build_system_prompt() -> str:
    return "\n".join(SYSTEM_RULES)


def _prepare_fragment(fragment: ContextFragment) -> Tuple[ContextFragment, PiiDetectionResult]:
    result = redact_pii(fragment.text)
    cleaned = fragment.copy(update={"text": result.redacted_text})
    return cleaned, result


def redact_case_meta(case_meta: Dict[str, object]) -> Tuple[Dict[str, object], bool]:
    detected = False
    sanitized = {}
    for key, value in case_meta.items():
        if isinstance(value, str):
            result = redact_pii(value)
            sanitized[key] = result.redacted_text
            detected = detected or result.detected
        else:
            sanitized[key] = value
    return sanitized, detected


def build_user_prompt(
    request: GenerateDraftRequest,
    fragments: Iterable[ContextFragment],
    schema_hint: Dict[str, object],
) -> Tuple[str, bool]:
    """Construct the user message for the LLM and return if PII was detected."""

    redacted_fragments: List[Dict[str, object]] = []
    pii_detected = False
    for fragment in fragments:
        cleaned, result = _prepare_fragment(fragment)
        pii_detected = pii_detected or result.detected
        redacted_fragments.append(
            {
                "doc_id": cleaned.doc_id,
                "fragment_id": cleaned.fragment_id,
                "text": cleaned.text,
                "metadata": cleaned.metadata.model_dump(),
                "score": cleaned.score,
            }
        )

    sanitized_meta, meta_pii = redact_case_meta(request.case_meta)
    pii_detected = pii_detected or meta_pii

    payload = {
        "query": redact_pii(request.query).redacted_text,
        "case_meta": sanitized_meta,
        "template_hint": request.template_hint.value if request.template_hint else None,
        "fragments": redacted_fragments,
        "history_summary": [entry.body_markdown[:200] for entry in request.history or []],
        "schema": schema_hint,
    }

    return json.dumps(payload, ensure_ascii=False, indent=2), pii_detected
