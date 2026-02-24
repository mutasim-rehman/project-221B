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
from src.query import (
    Mode,
    generate_answer,
    generate_character_reply,
    generate_ooc_explanation,
    generate_scene_reply,
    retrieve,
)
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


def _is_ooc_request(text: str) -> bool:
    """Detect whether the user is explicitly asking to step out of character."""
    if not text:
        return False
    lowered = text.strip().lower()
    if lowered.startswith("/explain"):
        return True
    if "/ooc" in lowered:
        return True
    if "step out of character" in lowered or "out of character" in lowered:
        return True
    return False


def _strip_ooc_prefix(text: str) -> str:
    """Remove a leading OOC command prefix like '/explain' while keeping the rest."""
    if not text:
        return text
    stripped = text.lstrip()
    if stripped.lower().startswith("/explain"):
        # Keep anything after the command as the real question, if present.
        remainder = stripped[len("/explain") :].strip()
        return remainder or text
    return text


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
    """Run a single character_chat turn with per-session memory and structured output.

    Supports both in-character replies and out-of-character (OOC) explanation mode.
    OOC requests are triggered by commands like '/explain', '/ooc', or phrases such
    as 'step out of character'.
    """
    # Detect and normalise any out-of-character commands.
    is_ooc = _is_ooc_request(question)
    effective_question = _strip_ooc_prefix(question) if is_ooc else question

    # Character-aware retrieval based on metadata.
    docs, metas = _retrieve_for_character(effective_question, character_key, top_k=CHAT_TOP_K)

    # History of in-character turns, used by both IC and OOC paths.
    history_ic = get_history(session_id, Mode.CHARACTER_CHAT.value, character_key)

    if is_ooc:
        # Route to explanation mode that comments on the fiction and prior conversation.
        reply = generate_ooc_explanation(character_key, effective_question, docs, metas, history_ic)
        append_turn(
            session_id,
            Mode.OOC_EXPLAIN.value,
            character_key,
            user_text=question,
            assistant_text=reply,
        )
        cfg = CHARACTERS[character_key]
        return {
            "reply": reply,
            "character": cfg["name"],
            "sources": _titles_from_metas(metas),
            "entities": _entities_from_metas(metas),
            "mode": Mode.OOC_EXPLAIN.value,
            "strictness": strictness,
            "ooc": True,
        }

    # Normal in-character path.
    strict_text = _strictness_preamble(strictness)
    if strictness:
        question_for_llm = f"{effective_question}\n\nStrictness profile: {strictness}.\n{strict_text}"
    else:
        question_for_llm = effective_question

    reply = generate_character_reply(character_key, question_for_llm, docs, metas, history_ic)

    append_turn(
        session_id,
        Mode.CHARACTER_CHAT.value,
        character_key,
        user_text=question,
        assistant_text=reply,
    )

    cfg = CHARACTERS[character_key]
    return {
        "reply": reply,
        "character": cfg["name"],
        "sources": _titles_from_metas(metas),
        "entities": _entities_from_metas(metas),
        "mode": Mode.CHARACTER_CHAT.value,
        "strictness": strictness,
        "ooc": False,
    }


def scene_chat_turn(
    character_keys,
    question: str,
    session_id: str,
    strictness: str = "balanced",
):
    """Run a multi-character 'scene' turn between 2–3 characters.

    Returns a structured object with the generated scene, participating characters,
    and basic retrieval metadata. This is backend-only; a frontend can render the
    dialogue by splitting on speaker tags like 'Sherlock Holmes:'.
    """
    if not character_keys:
        raise ValueError("scene_chat_turn requires at least one character key.")

    keys = [str(k).strip().lower() for k in character_keys]
    # Validate and deduplicate while preserving order.
    seen = set()
    validated_keys = []
    for key in keys:
        if not key or key in seen:
            continue
        if key not in CHARACTERS:
            raise ValueError(f"Unknown character key for scene chat: {key!r}")
        seen.add(key)
        validated_keys.append(key)

    if len(validated_keys) < 2 or len(validated_keys) > 3:
        raise ValueError("scene_chat_turn currently supports 2–3 distinct characters.")

    # Generic retrieval for the situation; the LLM will specialise per persona.
    docs, metas = retrieve(question, top_k=CHAT_TOP_K)

    # Use a composite key for scene memory so that scenes between different casts do not mix.
    scene_id = "scene:" + "+".join(validated_keys)
    history = get_history(session_id, Mode.SCENE_CHAT.value, scene_id)

    strict_text = _strictness_preamble(strictness)
    if strictness:
        question_for_llm = f"{question}\n\nStrictness profile: {strictness}.\n{strict_text}"
    else:
        question_for_llm = question

    scene_text = generate_scene_reply(validated_keys, question_for_llm, docs, metas, history)

    append_turn(
        session_id,
        Mode.SCENE_CHAT.value,
        scene_id,
        user_text=question,
        assistant_text=scene_text,
    )

    characters = [CHARACTERS[k]["name"] for k in validated_keys]
    return {
        "scene": scene_text,
        "characters": characters,
        "sources": _titles_from_metas(metas),
        "entities": _entities_from_metas(metas),
        "mode": Mode.SCENE_CHAT.value,
        "strictness": strictness,
    }

