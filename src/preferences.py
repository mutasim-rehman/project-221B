"""Simple per-user preference profiles for future personalisation.

Preferences are stored in a small JSON file keyed by user id. This is intended
as a minimal, file-based implementation suitable for a single-node deployment
or local development. A real multi-user deployment would likely swap this for
database-backed storage.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict

from src.config import ROOT


PREFERENCES_PATH = ROOT / "data" / "preferences.json"


@dataclass
class UserPreferences:
    favourite_character: str | None = None
    strictness: str = "canon_strict"  # e.g. "canon_strict" vs "looser"
    verbosity: str = "normal"  # "short", "normal", "verbose"


def _ensure_storage_dir() -> None:
    PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_all() -> Dict[str, UserPreferences]:
    if not PREFERENCES_PATH.exists():
        return {}
    try:
        raw = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, UserPreferences] = {}
    for user_id, data in raw.items():
        if not isinstance(data, dict):
            continue
        out[user_id] = UserPreferences(
            favourite_character=data.get("favourite_character"),
            strictness=data.get("strictness", "canon_strict"),
            verbosity=data.get("verbosity", "normal"),
        )
    return out


def _dump_all(prefs: Dict[str, UserPreferences]) -> None:
    _ensure_storage_dir()
    serialised = {uid: asdict(p) for uid, p in prefs.items()}
    PREFERENCES_PATH.write_text(json.dumps(serialised, indent=2, ensure_ascii=False), encoding="utf-8")


def get_preferences(user_id: str) -> UserPreferences:
    """Return preferences for the given user id, or defaults if none exist."""
    all_prefs = _load_all()
    return all_prefs.get(user_id, UserPreferences())


def set_preferences(user_id: str, prefs: UserPreferences) -> None:
    """Persist preferences for the given user id."""
    all_prefs = _load_all()
    all_prefs[user_id] = prefs
    _dump_all(all_prefs)

