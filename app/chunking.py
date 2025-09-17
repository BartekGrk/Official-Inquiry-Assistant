"""Document chunking utilities following the hybrid legal-aware strategy."""
from __future__ import annotations

import re
from typing import Iterable, List, Sequence

import tiktoken

_STRUCTURE_PATTERN = re.compile(
    r"(?=^\s*(DZIAŁ\s+[IVXLC]+|ROZDZIAŁ\s+[0-9IVXLC]+|Art\.\s*\d+[a-zA-Z]*|§\s*\d+|ust\.\s*\d+))",
    re.MULTILINE,
)

TOKEN_LIMIT = 1000
TOKEN_OVERLAP = 150
FALLBACK_MULTIPLIER = 1.5
ENCODING_NAME = "cl100k_base"


class ChunkingError(RuntimeError):
    """Raised when text cannot be chunked appropriately."""


def _encoding():
    return tiktoken.get_encoding(ENCODING_NAME)


def split_by_structure(text: str) -> List[str]:
    """Split ``text`` using legal structure markers.

    Ensures each returned block starts with a recognised legal heading when possible.
    """

    matches = list(_STRUCTURE_PATTERN.finditer(text))
    if not matches:
        return [text]

    sections: List[str] = []
    last_idx = 0
    for match in matches:
        start = match.start()
        if start != last_idx:
            sections.append(text[last_idx:start])
        last_idx = start
    if last_idx < len(text):
        sections.append(text[last_idx:])
    return [section.strip() for section in sections if section.strip()]


def _split_tokens(tokens: Sequence[int], chunk_size: int) -> Iterable[Sequence[int]]:
    for start in range(0, len(tokens), chunk_size):
        yield tokens[start : start + chunk_size]


def _fallback_split(section: str, chunk_size: int) -> List[str]:
    encoding = _encoding()
    tokens = encoding.encode(section)
    chunks = []
    for token_block in _split_tokens(tokens, chunk_size):
        text = encoding.decode(token_block).strip()
        if text:
            chunks.append(text)
    return chunks


def chunk_text(
    text: str,
    target_tokens: int = TOKEN_LIMIT,
    overlap_tokens: int = TOKEN_OVERLAP,
) -> List[str]:
    """Chunk ``text`` into ~target_tokens sized blocks preserving structure."""

    encoding = _encoding()
    sections = split_by_structure(text)
    chunks: List[str] = []

    current_tokens: List[int] = []
    for section in sections:
        section_tokens = encoding.encode(section)
        if len(section_tokens) > int(FALLBACK_MULTIPLIER * target_tokens):
            # Split extremely long sections
            for part in _fallback_split(section, target_tokens):
                part_tokens = encoding.encode(part)
                if current_tokens:
                    # flush existing tokens before adding fallback part
                    chunks.append(encoding.decode(current_tokens).strip())
                    current_tokens = []
                chunks.append(part)
                # start new chunk with overlap tokens from end of part
                if overlap_tokens and len(part_tokens) > overlap_tokens:
                    current_tokens = part_tokens[-overlap_tokens:]
                else:
                    current_tokens = part_tokens
            continue

        prospective_len = len(current_tokens) + len(section_tokens)
        if current_tokens and prospective_len > target_tokens:
            chunk = encoding.decode(current_tokens).strip()
            if chunk:
                chunks.append(chunk)
            if overlap_tokens and len(current_tokens) > overlap_tokens:
                current_tokens = current_tokens[-overlap_tokens:] + list(section_tokens)
            else:
                current_tokens = list(section_tokens)
        else:
            current_tokens.extend(section_tokens)

    if current_tokens:
        chunk = encoding.decode(current_tokens).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def chunk_document(text: str) -> List[str]:
    """Chunk the given legal document text according to MVP specification."""

    chunks = chunk_text(text)
    if not chunks:
        raise ChunkingError("Document could not be chunked into non-empty pieces")
    return chunks
