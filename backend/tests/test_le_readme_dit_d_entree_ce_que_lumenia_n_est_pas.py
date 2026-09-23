# -*- coding: utf-8 -*-
"""Ce que Lumenia n'est pas se lit dans l'ouverture du README, pas en bas de page.

23/09/2026 — décision d'Alex : Lumenia est publié en open source, il n'est pas hébergé. Or
l'ouverture du README disait « deployed with Docker » et rien d'autre ; « not a medical device »
et le 3114 n'arrivaient qu'à la toute dernière section. Quelqu'un qui lit l'ouverture d'un dépôt
de santé mentale doit y apprendre qu'il n'y a pas de service à joindre, que l'outil ne soigne
pas, et où appeler en cas de détresse.
"""
import re
from pathlib import Path

README = Path(__file__).resolve().parent.parent.parent / "README.md"


def _ouverture() -> str:
    texte = README.read_text(encoding="utf-8")
    fin = texte.find("\n## ")
    assert fin > 0, "témoin : le README doit avoir au moins une section"
    return texte[:fin]


def test_l_ouverture_dit_ce_que_lumenia_n_est_pas():
    ouverture = _ouverture()
    manquants = [dit for dit, motif in {
        "pas un service hébergé": r"not a hosted service",
        "pas un dispositif médical": r"not a medical device",
        "le 3114": r"\b3114\b",
    }.items() if not re.search(motif, ouverture, re.I)]
    assert manquants == [], f"l'ouverture du README ne dit pas : {manquants}"
