"""Command line interface for building the FAISS index from legal documents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import faiss
import numpy as np
import yaml
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

from app.chunking import chunk_document
from app.config import settings


def load_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def load_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_metadata(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"Metadata file missing for {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def iter_documents(doc_dir: Path) -> Iterable[Tuple[Path, Dict, str]]:
    for file_path in sorted(doc_dir.glob("*")):
        if file_path.suffix.lower() not in {".pdf", ".txt"}:
            continue
        meta_path = file_path.with_suffix(".meta.yaml")
        metadata = load_metadata(meta_path)
        if file_path.suffix.lower() == ".pdf":
            text = load_text_from_pdf(file_path)
        else:
            text = load_text_from_txt(file_path)
        yield file_path, metadata, text


def build_index(docs_path: Path, store_path: Path) -> None:
    docs = list(iter_documents(docs_path))
    if not docs:
        raise RuntimeError("No documents found for ingestion")

    encoder = SentenceTransformer(settings.embedding_model)

    fragments: List[Dict] = []
    embeddings: List[np.ndarray] = []

    for file_path, metadata, text in docs:
        doc_id = metadata.get("doc_id") or file_path.stem
        chunks = chunk_document(text)
        normalized_embeddings = encoder.encode(chunks, normalize_embeddings=True)
        for idx, (chunk, embedding) in enumerate(zip(chunks, normalized_embeddings)):
            fragment_id = f"{doc_id}-{idx:04d}"
            fragment_meta = {
                "doc_id": doc_id,
                "fragment_id": fragment_id,
                "text": chunk,
                "metadata": {
                    "doc_id": doc_id,
                    "tytul": metadata.get("tytul"),
                    "data_dokumentu": metadata.get("data_dokumentu"),
                    "is_binding_law": metadata.get("is_binding_law", False),
                    "source_path": str(file_path),
                },
            }
            fragments.append(fragment_meta)
            embeddings.append(np.asarray(embedding, dtype="float32"))

    matrix = np.vstack(embeddings)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    store_path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(store_path / "index.faiss"))
    with open(store_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(fragments, f, ensure_ascii=False, indent=2)

    print(f"Ingested {len(fragments)} fragments from {len(docs)} documents.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into FAISS index")
    parser.add_argument("--docs", type=Path, default=Path("data/docs"))
    parser.add_argument("--store", type=Path, default=Path("app/store"))
    args = parser.parse_args()

    build_index(args.docs, args.store)


if __name__ == "__main__":
    main()
