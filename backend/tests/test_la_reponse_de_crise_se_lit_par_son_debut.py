"""Quand un message évoque une détresse, l'écran montre le DÉBUT de la réponse, pas sa fin.

23/09/2026 — bannière de sécurité vue pour la première fois dans un navigateur, à 375 px : elle prend
220 px en haut, la zone des messages en garde 349, et `showSafetyBanner` défilait jusqu'en BAS.
La première phrase de la réponse de crise, celle qui présente le 3114, sortait de l'écran ; on voyait
la liste 15 / 112 et « Je reste là ». Pour cette réponse-là, c'est le début qu'on lit d'abord.
"""
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_la_banniere_montre_le_debut_de_la_reponse():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    debut = js.index("function showSafetyBanner")
    corps = js[debut:js.index("\n  }\n", debut)]
    assert "scrollToEnd" not in corps, "la bannière défile encore jusqu'à la fin de la réponse"
    assert "scrollIntoView" in corps, "le début de la réponse de crise n'est pas amené à l'écran"
