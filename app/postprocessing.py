"""Post-processing and validation of LLM outputs."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

from fastapi import HTTPException, status
from rapidfuzz import fuzz

from app.logging_config import logger
from app.schemas import DraftOutput, GenerateDraftResponse, HistoryEntry
from app.utils.pii import redact_pii


def detect_duplicate(body: str, history: Iterable[HistoryEntry], threshold: float = 92.0) -> Optional[str]:
    """Return template type if the body is too similar to a previous draft."""

    for entry in history:
        score = fuzz.token_set_ratio(body, entry.body_markdown)
        if score >= threshold:
            return entry.template_type.value
    return None


def validate_output(raw: Dict, history: Iterable[HistoryEntry], pii_detected: bool = False) -> DraftOutput:
    try:
        draft = DraftOutput.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        logger.error("Draft output schema validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid LLM JSON output") from exc

    duplicate = detect_duplicate(draft.body_markdown, history)
    risks = draft.risks.copy(update={"duplicate_of": duplicate})

    pii_result = redact_pii(draft.body_markdown)
    risks = risks.copy(update={"risk_rodo": risks.risk_rodo or pii_result.detected or pii_detected})

    return draft.copy(update={"risks": risks})


def build_response(draft: DraftOutput, request_id: str, retrieved_fragments) -> GenerateDraftResponse:
    return GenerateDraftResponse(
        draft=draft,
        retrieved_fragments=retrieved_fragments,
        request_id=request_id,
        created_at=datetime.utcnow(),
    )
