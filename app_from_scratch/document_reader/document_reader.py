# Load pdfs
import fitz
from typing import List, Dict
from ..config import THRESHOLD_ENCODING_ISSUES
from .encoding_issues import fix_polish_pdf_text, should_fix_document

class OfficialDocumentHandler:
    def __init__(self, path):
        self.path = path
        self.threshold = THRESHOLD_ENCODING_ISSUES

    def load_document(self) -> List[Dict]:
        try:
            if not self.path.lower().endswith(".pdf"):
                raise ValueError("File is not a PDF")

            doc = fitz.open(self.path)
            total_pages = doc.page_count  # or len(doc)

            text_list: List[Dict] = []

            # Attempt: first 5 non-empty pages
            sample_texts = []
            for i in range(min(total_pages, 15)):  # up to 15 to catch 5 non-empty ones
                t = doc.load_page(i).get_text("text") or ""
                if t.strip():
                    sample_texts.append(t)
                    if len(sample_texts) >= 5:
                        break

            fix_all = should_fix_document(sample_texts, sample_pages=5)

            #  Actual reading of all pages
            for i in range(total_pages):
                page = doc.load_page(i)
                text = page.get_text("text") or ""
                if fix_all and text:
                    text = fix_polish_pdf_text(text)

                text_list.append({"page": i + 1, "text": text})

            return text_list
        except Exception as e:
            print(f"Error loading PDF: {e}")
            return []
