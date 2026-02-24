"""In-memory per-session conversation memory for RAG turns.

This is intentionally simple and process-local. It is suitable for a single
process CLI or dev server; a production deployment would likely replace this
module with something backed by a shared store (Redis, database, etc.).
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple


Turn = Tuple[str, str]  # (user_text, assistant_text)
Key = Tuple[str, str, Optional[str]]  # (session_id, mode, character_key)

_MAX_TURNS_DEFAULT = 6
_MEMORY: Dict[Key, Deque[Turn]] = {}


def _key(session_id: str, mode: str, character_key: Optional[str]) -> Key:
    return session_id, mode, character_key


def get_history(
    session_id: str,
    mode: str,
    character_key: Optional[str],
    max_turns: int = _MAX_TURNS_DEFAULT,
) -> List[Turn]:
    """Return up to the last `max_turns` turns for this session/mode/character."""
    dq = _MEMORY.get(_key(session_id, mode, character_key))
    if not dq:
        return []
    # Deques preserve order; we slice from the right-hand side.
    if max_turns <= 0:
        return list(dq)
    return list(dq)[-max_turns:]


def append_turn(
    session_id: str,
    mode: str,
    character_key: Optional[str],
    user_text: str,
    assistant_text: str,
    max_turns: int = _MAX_TURNS_DEFAULT,
) -> None:
    """Append a new turn and keep only the most recent `max_turns`."""
    key = _key(session_id, mode, character_key)
    dq = _MEMORY.get(key)
    if dq is None:
        dq = deque(maxlen=max_turns)
        _MEMORY[key] = dq
    dq.append((user_text, assistant_text))

