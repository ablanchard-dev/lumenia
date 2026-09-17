"""The consent screen must not promise that nothing leaves the device.

Before: "Tes echanges restent sur cet appareil. Rien n'est partage ni revendu." while
app/llm.py sends every message to an external LLM provider (Gemini, Cerebras, Groq,
Mistral). A false privacy promise at the moment of consent, on an app for vulnerable
people.
"""
from pathlib import Path

from app import llm

INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"


def test_consent_screen_discloses_external_llm_providers():
    html = INDEX.read_text(encoding="utf-8")
    assert "Rien n'est partagé" not in html
    assert "restent <strong>sur cet appareil</strong>" not in html
    for provider in ("Google", "Groq", "Cerebras", "Mistral"):
        assert provider in html, provider
    # the disclosure names every provider the code can actually call
    assert set(llm._PROVIDERS) <= {"gemini", "cerebras", "groq", "mistral"}
