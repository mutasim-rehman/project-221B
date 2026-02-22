"""Load Sherlock Holmes canon from raw text files."""
import re
from pathlib import Path
from typing import Iterator

from src.config import RAW_DIR


def _parse_filename(path: Path) -> tuple[str, str, str]:
    """Extract story id, title, and year from filename like '25-the-red-headed-league-1892.txt'."""
    stem = path.stem
    parts = stem.split("-")
    if len(parts) >= 3:
        sid = parts[0]
        year = parts[-1] if parts[-1].isdigit() else ""
        title = "-".join(parts[1:-1]) if parts[-1].isdigit() else stem
        return sid, title, year
    return "", stem, ""


def _infer_collection(relative_path: str) -> str:
    """Infer collection (novels, adventures, etc.) from path."""
    if "novels" in relative_path:
        return "novels"
    if "the-adventures" in relative_path:
        return "adventures"
    if "the-memoirs" in relative_path:
        return "memoirs"
    if "the-return" in relative_path:
        return "return"
    if "his-last-bow" in relative_path:
        return "his_last_bow"
    if "the-case-book" in relative_path:
        return "case_book"
    return "unknown"


def load_documents() -> Iterator[dict]:
    """Yield documents from all .txt files in raw/."""
    for path in sorted(RAW_DIR.rglob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
            continue

        text = text.strip()
        if not text:
            continue

        rel = str(path.relative_to(RAW_DIR))
        sid, title, year = _parse_filename(path)
        collection = _infer_collection(rel)
        title_human = re.sub(r"-", " ", title).title()

        yield {
            "id": path.stem,
            "path": str(path),
            "title": title_human,
            "collection": collection,
            "year": year,
            "content": text,
        }
