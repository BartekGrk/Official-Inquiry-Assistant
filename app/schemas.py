"""Pydantic models for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateType(str, Enum):
    ACK = "ack"
    WEZWANIE_BRAKI = "wezwanie_braki"
    DUPLIKAT = "duplikat"
    PRZEKAZANIE = "przekazanie"
    PRZEDLUZENIE = "przedluzenie"


class FragmentMetadata(BaseModel):
    doc_id: str
    tytul: Optional[str] = None
    data_dokumentu: Optional[str] = None
    is_binding_law: Optional[bool] = None
    source_path: Optional[str] = None


class ContextFragment(BaseModel):
    doc_id: str
    fragment_id: str
    text: str
    metadata: FragmentMetadata
    score: Optional[float] = None


class HistoryEntry(BaseModel):
    template_type: TemplateType
    body_markdown: str
    citations: List[str] = Field(default_factory=list)


class GenerateDraftRequest(BaseModel):
    query: str
    case_meta: Dict[str, Any]
    template_hint: Optional[TemplateType] = None
    context_docs: Optional[List[ContextFragment]] = None
    history: Optional[List[HistoryEntry]] = None


class RiskReport(BaseModel):
    risk_rodo: bool = False
    duplicate_of: Optional[str] = None


class DraftOutput(BaseModel):
    template_type: TemplateType
    body_markdown: str
    citations: List[str]
    legal_basis: List[str]
    required_clarifications: List[str]
    risks: RiskReport

    @field_validator("citations")
    @classmethod
    def ensure_citations(cls, value: List[str]) -> List[str]:
        if len(value) < 2:
            raise ValueError("At least two citations are required")
        return value

    @field_validator("legal_basis")
    @classmethod
    def ensure_legal_basis(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("legal_basis cannot be empty")
        return value


class GenerateDraftResponse(BaseModel):
    draft: DraftOutput
    retrieved_fragments: Optional[List[ContextFragment]] = None
    request_id: str
    created_at: datetime
