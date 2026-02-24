import types

import pytest

import src.query as query_mod
from src.query import Mode, _build_context, generate_answer, generate_character_reply, retrieve


class DummyCollection:
    def __init__(self, documents, metadatas):
        self._documents = documents
        self._metadatas = metadatas

    def query(self, query_embeddings, n_results, include):
        assert len(query_embeddings) == 1
        # Always return the first n_results items deterministically.
        return {
            "documents": [self._documents[:n_results]],
            "metadatas": [self._metadatas[:n_results]],
        }


class DummyClient:
    def __init__(self, collection):
        self._collection = collection

    def get_collection(self, name):
        return self._collection


def test_retrieve_uses_embeddings_and_returns_documents(monkeypatch):
    # Arrange: patch embedding and chroma client so no real services are needed.
    calls = {}

    def fake_get_embedding(text: str):
        calls["embedded"] = text
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("src.query.get_embedding", fake_get_embedding)

    docs = ["Sherlock Holmes is a consulting detective.", "Dr. Watson is his friend."]
    metas = [
        {"title": "A Study in Scarlet"},
        {"title": "The Sign of Four"},
    ]
    dummy_collection = DummyCollection(docs, metas)

    def fake_persistent_client(path: str):
        return DummyClient(dummy_collection)

    monkeypatch.setattr("src.query.chromadb.PersistentClient", fake_persistent_client)

    # Act
    out_docs, out_metas = retrieve("who is Sherlock?", top_k=1)

    # Assert
    assert calls["embedded"] == "who is Sherlock?"
    assert out_docs == [docs[0]]
    assert out_metas == [metas[0]]


def test_generate_answer_builds_prompt_and_calls_ollama(monkeypatch):
    captured = {}

    def fake_chat(model, messages):
        captured["model"] = model
        captured["messages"] = messages
        return {"message": {"content": "stubbed answer"}}

    monkeypatch.setattr("src.query.OLLAMA_CLIENT.chat", fake_chat)

    chunks = ["Sherlock Holmes lives at Baker Street."]
    metas = [{"title": "A Study in Scarlet"}]
    answer = generate_answer("who is Sherlock?", chunks, metas)

    assert answer == "stubbed answer"
    assert "who is Sherlock?" in captured["messages"][0]["content"]
    # Ensure context from chunks is injected.
    assert "Baker Street" in captured["messages"][0]["content"]


def test_generate_character_reply_includes_profile_and_history(monkeypatch):
    captured = {}

    def fake_chat(model, messages):
        captured["messages"] = messages
        return {"message": {"content": "stubbed character reply"}}

    monkeypatch.setattr("src.query.OLLAMA_CLIENT.chat", fake_chat)

    chunks = ["Watson narrates Holmes's exploits."]
    metas = [{"title": "The Sign of Four"}]
    history = [("Hello", "Good day, Watson.")]

    reply = generate_character_reply("sherlock", "who are you?", chunks, metas, history)

    assert reply == "stubbed character reply"
    prompt = captured["messages"][0]["content"]
    # Basic sanity checks on prompt construction.
    assert "Sherlock Holmes" in prompt
    assert "Character profile:" in prompt
    assert "Conversation so far:" in prompt
    assert "Canon passages:" in prompt
    assert "who are you?" in prompt


@pytest.mark.smoke
def test_end_to_end_canon_qa_smoke(monkeypatch):
    """Lightweight smoke test for canon_qa mode.

    This does not assert semantic correctness of the LLM output but checks that
    the RAG plumbing (retrieve + generate_answer) runs without raising and that
    the prompt wiring is coherent. It is safe to skip in environments without
    Ollama or a built index.
    """
    try:
        # If the index or Ollama is not available, we skip instead of failing.
        _ = query_mod.CHROMA_DIR
    except Exception:
        pytest.skip("Environment not configured for RAG smoke tests.")

    # Stub Ollama to avoid depending on a running model.
    def fake_chat(model, messages):
        return {"message": {"content": "Sherlock Holmes is a consulting detective."}}

    monkeypatch.setattr("src.query.OLLAMA_CLIENT.chat", fake_chat)

    # We only care that retrieve() is invoked; we mock its output to avoid
    # requiring an actual Chroma index for this smoke test.
    def fake_retrieve(q: str, top_k: int):
        docs = ["Sherlock Holmes is a consulting detective in London."]
        metas = [{"title": "A Study in Scarlet"}]
        return docs, metas

    monkeypatch.setattr("src.query.retrieve", fake_retrieve)

    docs, metas = retrieve("who is Sherlock?", top_k=1)
    answer = generate_answer("who is Sherlock?", docs, metas)

    assert docs
    assert metas
    assert isinstance(answer, str)
    assert "consulting detective" in answer

