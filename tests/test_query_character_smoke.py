import pytest

from src.query import generate_character_reply


@pytest.mark.smoke
def test_character_reply_smoke_sherlock(monkeypatch):
    """Smoke test that Sherlock persona wiring is coherent."""
    captured = {}

    def fake_chat(model, messages):
        captured["messages"] = messages
        return {"message": {"content": "I am Sherlock Holmes, a consulting detective."}}

    monkeypatch.setattr("src.query.ollama.chat", fake_chat)

    chunks = ["Sherlock Holmes is a consulting detective in London."]
    metas = [{"title": "A Study in Scarlet"}]
    history = [("Who are you?", "I am a detective.")]

    reply = generate_character_reply("sherlock", "who are you?", chunks, metas, history)

    assert "Sherlock Holmes" in captured["messages"][0]["content"]
    assert "Character profile:" in captured["messages"][0]["content"]
    assert isinstance(reply, str)


@pytest.mark.smoke
def test_character_reply_smoke_watson(monkeypatch):
    """Smoke test that Watson persona wiring is coherent."""
    captured = {}

    def fake_chat(model, messages):
        captured["messages"] = messages
        return {"message": {"content": "I am Dr. John Watson, Holmes's friend and chronicler."}}

    monkeypatch.setattr("src.query.ollama.chat", fake_chat)

    chunks = ["Dr. Watson narrates many of Holmes's cases."]
    metas = [{"title": "The Sign of Four"}]
    history = [("Who are you?", "I am a doctor.")]

    reply = generate_character_reply("watson", "who are you?", chunks, metas, history)

    assert "Dr. John Watson" in captured["messages"][0]["content"]
    assert "Character profile:" in captured["messages"][0]["content"]
    assert isinstance(reply, str)

