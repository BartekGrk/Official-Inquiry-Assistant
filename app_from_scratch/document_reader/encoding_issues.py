import re
from config import PL, COMMON_OK
from typing import  Sequence

GLYPH_SUBS = {
    "Ê": "ś",
    "´": "ę",
    "∏": "ł",
    "à": "ą",
    "˝": "ż",
    "ƒ": "ń",
    "ç": "ć",
    "ê": "ź",
}

GLYPH_MAP = str.maketrans(GLYPH_SUBS)

BAD_GLYPHS = tuple(GLYPH_SUBS.keys())

# A few marker substrings (optional "bonus" detection)
MARKERS = (
    "wrzeÊ",    # wrześ...
    "dost´p",   # dostę...
    "Rozdzia∏", # Rozdział
    "Ka˝",      # Każ...
    "wglàd",    # wgląd...
    "Paƒ",      # Pań...
    "posiedzeƒ" # posiedzeń
)

# Heuristics (waiting for better data)
DEFAULT_GARBLE_THRESHOLD = 0.02   # 2% of bad glyphs
DEFAULT_MIN_GLYPH_HITS = 2        # already 2 hits of BAD_GLYPHS is a pretty strong signal


def glyph_hits(text: str) -> int:
    """Count the bad glyphs in the text."""
    if not text:
        return 0
    return sum(text.count(ch) for ch in BAD_GLYPHS)


def garble_score(text: str) -> float:
    """
    Score 0..1. The higher, the better the chance of bad glyphs.
    Note: this score doesn't try to be linguistically smart — it just needs to be simple and stable.
    """
    if not text:
        return 1.0

    # 1) The weakest signal: the occurrence of known "garbles"
    hits = glyph_hits(text)
    if hits:
        # We normalize to the length of the text, but "reward" a few hits with a strong signal.
        base = min(1.0, (hits / max(1, len(text))) * 50.0)  # 50x = rapid convergence
    else:
        base = 0.0

    # 2) A medium signal: many characters >127 not being PL or common punctuation
    #    (note: in correct PDFs, there may be "—", "„" etc., so we treat this signal lightly)
    bad = 0
    total = 0
    for ch in text:
        total += 1
        if ch in PL or ch in COMMON_OK:
            continue
        o = ord(ch)
        if o > 127:
            bad += 1

    ratio = bad / max(1, total)

    # 3) Bonus za markery
    marker_hits = sum(text.count(m) for m in MARKERS)

    score = max(base, ratio)
    if marker_hits:
        score = min(1.0, score + 0.15)

    return score

def should_fix_document(
    pages_text: Sequence[str],
    sample_pages: int = 5,
    threshold: float = DEFAULT_GARBLE_THRESHOLD,
    min_glyph_hits: int = DEFAULT_MIN_GLYPH_HITS,
) -> bool:
    """
    Decision if we should try to fix document encoding.

    """
    scores = []
    total_hits = 0
    seen = 0

    for t in pages_text:
        if not t or not t.strip():
            continue
        total_hits += glyph_hits(t)
        scores.append(garble_score(t))
        seen += 1
        if seen >= sample_pages:
            break

    if not scores:
        # No text -> we don't know; assume it's a scanned/OCR document
        return False

    # If we have a known "garble" (a misencoded character), don't hesitate
    if total_hits >= min_glyph_hits:
        return True

    # Otherwise, average the score
    avg = sum(scores) / len(scores)
    return avg >= threshold


_SENTENCE_CASE_RE = re.compile(r'(^|[.!?]\s+|\n\s*)([ąćęłńóśżź])')


def fix_polish_pdf_text(text: str) -> str:
    if not text:
        return text

    out = text.translate(GLYPH_MAP)

    # fix sentence case (uppercase first letter)
    def up(m: re.Match) -> str:
        return m.group(1) + m.group(2).upper()

    out = _SENTENCE_CASE_RE.sub(up, out)
    return out