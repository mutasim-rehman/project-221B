"""Load Sherlock Holmes canon from raw text files."""
import re
from pathlib import Path
from typing import Iterator

from src.config import RAW_DIR, CHARACTERS


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


def _infer_story_type(collection: str) -> str:
    """Classify stories into a coarse type for metadata."""
    if collection == "novels":
        return "novel"
    if collection in {
        "adventures",
        "memoirs",
        "return",
        "his_last_bow",
        "case_book",
    }:
        return "short_story"
    return "unknown"


def _extract_characters(text: str) -> list[str]:
    """Heuristically extract major recurring characters present in the text.

    This is intentionally conservative: we only mark a character as present
    if their name (or a distinctive part of it) occurs in the story text.
    """
    lowered = text.lower()
    found: set[str] = set()

    for cfg in CHARACTERS.values():
        name = cfg.get("name", "")
        if not name:
            continue
        # Match either the full name or the surname as a rough heuristic.
        parts = name.split()
        surname = parts[-1].lower() if parts else ""
        if name.lower() in lowered or (surname and surname in lowered):
            found.add(name)

    return sorted(found)


def load_documents() -> Iterator[dict]:
    """Yield documents from all .txt files in raw/ with rich metadata."""
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
        story_type = _infer_story_type(collection)
        title_human = re.sub(r"-", " ", title).title()
        characters = _extract_characters(text)

        yield {
            "id": path.stem,
            "path": str(path),
            "title": title_human,
            "collection": collection,
            "year": year,
            "story_type": story_type,
            "characters": characters,
            "content": text,
        }
