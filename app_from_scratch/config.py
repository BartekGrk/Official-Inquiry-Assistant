from pathlib import Path

PL = set("ąćęłńóśżźĄĆĘŁŃÓŚŻŹ")
COMMON_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \t\r\n.,:;!?()[]{}<>\"'/-–—+*=_%&@#")

SUSPECT = set("Ê∏´˝àÀÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß")

THRESHOLD_ENCODING_ISSUES = 0.4


BASE_DIR = Path(__file__).resolve().parent.parent        # .../app_from_scratch
DATA_DIR = BASE_DIR / "data" / "docs"

def pdf_path(filename: str) -> Path:
    return DATA_DIR / filename