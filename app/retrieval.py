"""Retrieval layer using FAISS and sentence-transformers.

The MVP favors this pairing because it is fully self-hostable, fast on CPU-only
hardware, and easy to reason about for a corpus that comfortably fits into a
single FAISS `IndexFlatIP`. The surrounding plumbing keeps the metadata schema
and scoring hooks generic so we can migrate to a managed vector database or
plug in heavier cross-encoder rerankers when scale demands it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Iterable, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.schemas import ContextFragment, FragmentMetadata


@dataclass
class RetrievedFragment:
    fragment: ContextFragment
    score: float


class RetrievalPipeline:
    """Load FAISS index and perform retrieval + heuristic reranking."""

    def __init__(self) -> None:
        self.model = SentenceTransformer(settings.embedding_model)
        self.index = self._load_index(settings.index_path)
        self.metadata = self._load_metadata(settings.meta_path)

    @staticmethod
    def _load_index(path: str) -> Optional[faiss.Index]:
        if not os.path.exists(path):
            return None
        return faiss.read_index(path)

    @staticmethod
    def _load_metadata(path: str) -> List[dict]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _search(self, query: str, top_k: int) -> Iterable[RetrievedFragment]:
        if self.index is None:
            return []
        query_emb = self.model.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(np.array(query_emb).astype("float32"), top_k)
        retrieved: List[RetrievedFragment] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            fragment = ContextFragment(
                doc_id=meta["doc_id"],
                fragment_id=meta["fragment_id"],
                text=meta["text"],
                metadata=FragmentMetadata(**meta["metadata"]),
                score=float(score),
            )
            retrieved.append(RetrievedFragment(fragment=fragment, score=float(score)))
        return retrieved

    @staticmethod
    def _heuristic_score(fragment: ContextFragment, base_score: float) -> float:
        metadata = fragment.metadata
        score = base_score
        if metadata.is_binding_law:
            score += 0.1
        if metadata.data_dokumentu:
            try:
                doc_date = datetime.fromisoformat(metadata.data_dokumentu)
                age_days = (datetime.utcnow() - doc_date).days
                # Newer documents receive a boost
                score += max(0.0, 0.05 * (1 - min(age_days / 3650, 1)))
            except ValueError:
                pass
        return score

    def retrieve(self, query: str, top_k: Optional[int] = None, rerank_k: Optional[int] = None) -> List[ContextFragment]:
        """Retrieve and rerank fragments for the query."""

        if self.index is None:
            return []

        top_k = top_k or settings.top_k
        rerank_k = rerank_k or settings.rerank_k

        retrieved = list(self._search(query, top_k))
        scored = [
            (self._heuristic_score(item.fragment, item.score), item.fragment)
            for item in retrieved
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [fragment for _, fragment in scored[:rerank_k]]


@lru_cache
def get_pipeline() -> RetrievalPipeline:
    return RetrievalPipeline()
