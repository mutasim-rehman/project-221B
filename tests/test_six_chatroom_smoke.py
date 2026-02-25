import pytest


@pytest.mark.smoke
def test_generate_chatroom_reply_smoke_includes_user_rule(monkeypatch):
    captured = {}

    def fake_chat(model, messages):
        captured["messages"] = messages
        return {"message": {"content": "Sherlock Holmes: Very well.\nDr. John Watson: Indeed."}}

    monkeypatch.setattr("src.query.OLLAMA_CLIENT.chat", fake_chat)

    from src.query import generate_chatroom_reply

    keys = ["sherlock", "watson", "moriarty", "irene", "lestrade", "mycroft"]
    chunks = ["Holmes lives at Baker Street with Dr. Watson."]
    metas = [{"title": "A Study in Scarlet"}]
    history = [("We all meet.", "Sherlock Holmes: Let us begin.")]

    out = generate_chatroom_reply(
        keys,
        "Start the meeting.",
        chunks,
        metas,
        history,
        include_user_in_room=True,
    )

    prompt = captured["messages"][0]["content"]
    assert "Sherlock Holmes:" in prompt
    assert "Dr. John Watson:" in prompt
    assert "Professor James Moriarty:" in prompt
    assert "Irene Adler:" in prompt
    assert "Inspector G. Lestrade:" in prompt
    assert "Mycroft Holmes:" in prompt
    assert "Do NOT write dialogue lines for the user" in prompt
    assert isinstance(out, str)


@pytest.mark.smoke
def test_generate_case_story_reply_smoke_includes_cast(monkeypatch):
    captured = {}

    def fake_chat(model, messages):
        captured["messages"] = messages
        return {"message": {"content": "A short pastiche story."}}

    monkeypatch.setattr("src.query.OLLAMA_CLIENT.chat", fake_chat)

    from src.query import generate_case_story_reply

    keys = ["sherlock", "watson", "moriarty", "irene", "lestrade", "mycroft"]
    chunks = ["A mysterious case begins in London."]
    metas = [{"title": "The Red-Headed League"}]
    history = []

    out = generate_case_story_reply(keys, "A theft at the Diogenes Club.", chunks, metas, history)

    prompt = captured["messages"][0]["content"]
    assert "Cast (must all appear meaningfully in this episode):" in prompt
    assert "Sherlock Holmes" in prompt
    assert "Dr. John Watson" in prompt
    assert "Professor James Moriarty" in prompt
    assert "Irene Adler" in prompt
    assert "Inspector G. Lestrade" in prompt
    assert "Mycroft Holmes" in prompt
    assert isinstance(out, str)

