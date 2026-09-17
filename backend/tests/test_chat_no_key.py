"""No LLM key configured: the user must be told why, not asked to retry forever."""
from app import chat


def test_chat_without_any_llm_key_says_so(monkeypatch):
    monkeypatch.setattr(chat, "_client", None)
    out = chat.chat_reply("organiser ma semaine", [], False, "normal", None)
    assert "Réessaie dans une minute" not in out["reply"]
    assert "clé" in out["reply"] and ".env" in out["reply"]
    assert out["risk"] is False
