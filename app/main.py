"""FastAPI application exposing the GovLetter-RAG MVP."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, status

from app.config import settings
from app.logging_config import configure_logging, logger
from app.postprocessing import build_response, validate_output
from app.prompting import build_system_prompt, build_user_prompt
from app.retrieval import RetrievalPipeline, get_pipeline
from app.schemas import ContextFragment, GenerateDraftRequest, GenerateDraftResponse
from app.services.llm_client import LLMClient, get_llm_client

configure_logging()
app = FastAPI(title="GovLetter-RAG", version="0.1.0")


@app.on_event("startup")
def warmup_retrieval() -> None:
    pipeline = get_pipeline()
    if pipeline.index is None:
        logger.warning("FAISS index not found at %s", settings.index_path)
    else:
        logger.info("Loaded retrieval index with %s fragments", len(pipeline.metadata))


@app.get("/healthz")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


def _schema_hint() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "template_type": {"enum": ["ack", "wezwanie_braki", "duplikat", "przekazanie", "przedluzenie"]},
            "body_markdown": {"type": "string", "description": "Final draft body in Markdown."},
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
            },
            "legal_basis": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "required_clarifications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "risks": {
                "type": "object",
                "properties": {
                    "risk_rodo": {"type": "boolean"},
                    "duplicate_of": {"type": ["string", "null"]},
                },
                "required": ["risk_rodo", "duplicate_of"],
            },
        },
        "required": [
            "template_type",
            "body_markdown",
            "citations",
            "legal_basis",
            "required_clarifications",
            "risks",
        ],
        "additionalProperties": False,
    }


@app.post("/generate-draft", response_model=GenerateDraftResponse)
def generate_draft(
    request: GenerateDraftRequest,
    pipeline: RetrievalPipeline = Depends(get_pipeline),
    llm: LLMClient = Depends(get_llm_client),
) -> GenerateDraftResponse:
    request_id = str(uuid.uuid4())

    fragments: List[ContextFragment]
    retrieved_fragments: List[ContextFragment] | None

    if request.context_docs:
        fragments = request.context_docs
        retrieved_fragments = None
    else:
        fragments = pipeline.retrieve(request.query, settings.top_k, settings.rerank_k)
        retrieved_fragments = fragments
        if not fragments:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Retrieval index unavailable or empty")

    system_prompt = build_system_prompt()
    user_payload, pii_detected = build_user_prompt(request, fragments, _schema_hint())

    try:
        raw_output = llm.complete_json(system_prompt, user_payload, _schema_hint())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM call failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM generation failed") from exc

    history = request.history or []
    draft = validate_output(raw_output, history, pii_detected=pii_detected)

    response = build_response(draft, request_id, retrieved_fragments)
    return response
