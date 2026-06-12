"""Tests de la détection de détresse (app.chat.detect_crisis).

Feature critique : un faux négatif = on rate un signal de crise ; un faux
positif = on affiche la bannière 3114 à tort (anxiogène). On teste les deux.
"""
import pytest

from app.chat import _normalize, detect_crisis


@pytest.mark.parametrize("msg", [
    "je pense au suicide",
    "j'ai des idées suicidaires",
    "je veux mourir",
    "j'ai plus envie de vivre",
    "envie de mourir",
    "je veux en finir",
    "j'ai des idées noires",
    "je veux me faire du mal",
    "je veux me tailler les veines",
    "je pense à la scarification",
    "je vais me pendre",
    "je veux sauter du pont",
])
def test_detects_french_distress(msg):
    assert detect_crisis(msg) is True


@pytest.mark.parametrize("msg", [
    "i want to die",
    "i'm going to kill myself",
    "i want to end it all",
    "i feel better off dead",
    "i want to hurt myself",
])
def test_detects_english_distress(msg):
    assert detect_crisis(msg) is True


def test_case_insensitive():
    assert detect_crisis("JE VEUX MOURIR") is True


def test_accent_insensitive():
    assert detect_crisis("j'ai des idees noires") is True


def test_detects_compact_obfuscated_form():
    # « s u i c i d e » écrit espacé pour contourner un filtre naïf
    assert detect_crisis("s u i c i d e") is True


@pytest.mark.parametrize("msg", [
    "je suis un peu fatigué aujourd'hui",
    "je n'arrive pas à me concentrer sur mon travail",
    "aide-moi à organiser ma journée",
    "j'ai raté mon examen et je suis déçu",
    "comment débloquer une tâche difficile ?",
    "",
])
def test_benign_messages_not_flagged(msg):
    assert detect_crisis(msg) is False


def test_normalize_lowercases_and_strips_accents():
    assert _normalize("ÉCRÀN Über") == "ecran uber"
