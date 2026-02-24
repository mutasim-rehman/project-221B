"""Backend-facing helpers for structured RAG turns.

These functions wrap the lower-level `src.query` primitives to provide:
- Per-session memory (using `session_memory`).
- Character-aware retrieval for character chat.
- Configurable "canon strictness" for Q&A.
- Structured response objects suitable for a frontend.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import chromadb

from src.cache import get_embedding
from src.config import CHROMA_DIR, COLLECTION_NAME, CHARACTERS, CHAT_TOP_K
from src.query import Mode, generate_answer, generate_character_reply, retrieve
from src.session_memory import append_turn, get_history


def _titles_from_metas(metas: List[dict]) -> List[str]:
    return [m.get("title", "?") for m in metas]


def _entities_from_metas(metas: List[dict]) -> List[str]:
    """Very lightweight entity extraction based on metadata."""
    chars: set[str] = set()
    for m in metas:
        for c in m.get("characters", []) or []:
            chars.add(c)
    return sorted(chars)


def _strictness_preamble(strictness: str) -> str:
    strictness = strictness.lower()
    if strictness == "creative":
        return (
            "You may extrapolate and add plausible details beyond the passages, "
            "but clearly mark any speculation as such. Do not contradict the passages."
        )
    if strictness == "balanced":
        return (
            "Answer primarily from the passages, but you may lightly paraphrase or "
            "fill in obvious gaps if it does not contradict the passages."
        )
    # strict (default)
    return (
        "Only answer using facts that can be supported by the passages. If the answer "
        "is not present, say that it is unknown from the provided passages."
    )


def _format_qa_history(turns) -> str:
    if not turns:
        return ""
    lines: List[str] = []
    for i, (user_text, assistant_text) in enumerate(turns, 1):
        lines.append(f"[{i}] Q: {user_text}\n    A: {assistant_text}")
    return "\n".join(lines)


def _retrieve_for_character(question: str, character_key: str, top_k: int = CHAT_TOP_K):
    """Retrieval that prefers passages mentioning the chosen character."""
    embedding = get_embedding(question)
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:  # pragma: no cover - defensive
        raise RuntimeError(
            f"Vector index not found at {CHROMA_DIR} (collection '{COLLECTION_NAME}'). "
            "Build it first by running: python -m src.index"
        ) from e

    char_name = CHARACTERS[character_key]["name"]
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where={"characters": {"$contains": char_name}},
        include=["documents", "metadatas"],
    )
    return results["documents"][0], results["metadatas"][0]


def canon_qa_turn(
    question: str,
    session_id: str,
    strictness: str = "strict",
) -> Dict[str, Any]:
    """Run a single canon_qa turn with per-session memory and structured output."""
    # Retrieval always uses the raw question.
    docs, metas = retrieve(question)

    # Include prior Q&A in the question passed into the LLM.
    history = get_history(session_id, Mode.CANON_QA.value, character_key=None)
    history_text = _format_qa_history(history)
    strict_text = _strictness_preamble(strictness)

    if history_text:
        question_for_llm = (
            f"{question}\n\nPrevious conversation (questions and answers so far):\n"
            f"{history_text}\n\nStrictness profile: {strictness}.\n{strict_text}"
        )
    else:
        question_for_llm = f"{question}\n\nStrictness profile: {strictness}.\n{strict_text}"

    answer = generate_answer(question_for_llm, docs, metas)

    append_turn(session_id, Mode.CANON_QA.value, character_key=None, user_text=question, assistant_text=answer)

    return {
        "answer": answer,
        "sources": _titles_from_metas(metas),
        "entities": _entities_from_metas(metas),
        "mode": Mode.CANON_QA.value,
        "strictness": strictness,
    }


def character_chat_turn(
    character_key: str,
    question: str,
    session_id: str,
    strictness: str = "strict",
) -> Dict[str, Any]:
    """Run a single character_chat turn with per-session memory and structured output."""
    # Character-aware retrieval based on metadata.
    docs, metas = _retrieve_for_character(question, character_key, top_k=CHAT_TOP_K)

    history = get_history(session_id, Mode.CHARACTER_CHAT.value, character_key)

    # For now, we keep strictness behaviour the same as canon_qa at the question level,
    # but still rely on the persona prompt to enforce in-character behaviour.
    strict_text = _strictness_preamble(strictness)
    if strictness:
        question_for_llm = f"{question}\n\nStrictness profile: {strictness}.\n{strict_text}"
    else:
        question_for_llm = question

    reply = generate_character_reply(character_key, question_for_llm, docs, metas, history)

    append_turn(session_id, Mode.CHARACTER_CHAT.value, character_key, user_text=question, assistant_text=reply)

    cfg = CHARACTERS[character_key]
    return {
        "reply": reply,
        "character": cfg["name"],
        "sources": _titles_from_metas(metas),
        "entities": _entities_from_metas(metas),
        "mode": Mode.CHARACTER_CHAT.value,
        "strictness": strictness,
    }

