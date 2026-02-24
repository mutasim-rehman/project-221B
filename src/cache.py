"""Simple in-process caching for embeddings and answers.

This module is intentionally lightweight and purely in-memory. It is meant as
an optimisation layer for the CLI and for future API workers; it does not
persist between processes.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Tuple


@lru_cache(maxsize=2048)
def _embedding_cache(text: str) -> Tuple[float, ...]:
    """Return a cached embedding for the given text.

    We delegate to `src.embeddings.get_embedding` but memoise the result in
    process memory to avoid repeated model inference for identical queries.
    """
    from src.embeddings import get_embedding as _raw_get_embedding

    # Convert to tuple so that results are hashable for the LRU cache.
    return tuple(_raw_get_embedding(text))


def get_embedding(text: str) -> list[float]:
    """Public entry point for cached single-text embeddings."""
    return list(_embedding_cache(text))


_ANSWER_CACHE: Dict[Tuple[str, str, Optional[str]], str] = {}


def _make_answer_key(mode: str, question: str, character_key: Optional[str]) -> Tuple[str, str, Optional[str]]:
    return mode, question.strip(), character_key


def get_cached_answer(mode: str, question: str, character_key: Optional[str]) -> Optional[str]:
    """Return a cached answer if present for (mode, question, character)."""
    key = _make_answer_key(mode, question, character_key)
    return _ANSWER_CACHE.get(key)


def store_answer(mode: str, question: str, character_key: Optional[str], answer: str) -> None:
    """Store an answer in the in-memory cache."""
    key = _make_answer_key(mode, question, character_key)
    _ANSWER_CACHE[key] = answer

