"""Offline evaluation harness for the Sherlock Holmes RAG.

This script runs a small set of canonical questions against the live RAG
pipeline (retrieve + generate_answer) and prints simple pass/fail metrics
based on whether expected phrases are present in the model's answer.

Usage:
    python eval/run_eval.py

Requirements:
- Chroma index built (run `python -m src.index` first).
- Ollama running with the configured model (`OLLAMA_MODEL`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.query import generate_answer, retrieve


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "eval" / "canonical_questions.json"


def load_questions() -> list[dict[str, Any]]:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    return list(data)


def normalise(text: str) -> str:
    return text.lower()


def evaluate_question(q: dict[str, Any]) -> dict[str, Any]:
    """Run RAG for a single question and compute simple metrics."""
    question = q["question"]
    expected = [e.lower() for e in q.get("expected_phrases", [])]

    docs, metas = retrieve(question)
    answer = generate_answer(question, docs, metas)

    answer_norm = normalise(answer)
    hits = [e for e in expected if e in answer_norm]
    return {
        "id": q["id"],
        "question": question,
        "expected_phrases": expected,
        "num_expected": len(expected),
        "num_hits": len(hits),
        "hits": hits,
        "answer_length": len(answer),
    }


def main() -> None:
    questions = load_questions()
    print(f"Loaded {len(questions)} canonical questions from {QUESTIONS_PATH}")

    results: list[dict[str, Any]] = []
    for q in questions:
        print(f"\n=== {q['id']} ===")
        try:
            res = evaluate_question(q)
        except Exception as e:  # pragma: no cover - used as a manual harness
            print(f"ERROR while evaluating '{q['id']}': {e}")
            continue
        results.append(res)
        print(f"Question: {res['question']}")
        print(f"Expected phrases: {', '.join(res['expected_phrases']) or '-'}")
        print(f"Hits: {', '.join(res['hits']) or '-'}")
        print(f"Answer length (chars): {res['answer_length']}")

    if not results:
        print("\nNo successful evaluations ran.")
        return

    total_expected = sum(r["num_expected"] for r in results)
    total_hits = sum(r["num_hits"] for r in results)
    overall_recall = (total_hits / total_expected) if total_expected else 0.0

    print("\n=== Summary ===")
    print(f"Questions run: {len(results)}")
    print(f"Total expected phrases: {total_expected}")
    print(f"Total hits: {total_hits}")
    print(f"Approx. phrase-level recall: {overall_recall:.2%}")


if __name__ == "__main__":
    main()

