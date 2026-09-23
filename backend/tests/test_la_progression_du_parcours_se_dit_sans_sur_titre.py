"""La progression du parcours se lit sur la barre, pas dans un sur-titre en capitales.

23/09/2026 — critique Impeccable : au-dessus de chaque question, « ÉPREUVE 1 SUR 30 —
COMPRÉHENSION VERBALE » en capitales espacées, le petit badge posé sur chaque titre des gabarits
(interdit par le plancher de qualité), avec un tiret cadratin. Et la barre de progression était
`aria-hidden` : pour un lecteur d'écran, ce sur-titre était la SEULE trace de la progression.

Maintenant : la barre est un `progressbar` (valeurs + texte « Épreuve 3 sur 30 : … »), un compteur
discret l'accompagne, et plus rien n'est en capitales au-dessus de la question.
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_la_barre_de_progression_est_annoncee():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    barre = re.search(r'<div[^>]*id="parcours-progress"[^>]*>', html)
    assert barre, "témoin : la barre du parcours doit exister"
    assert 'role="progressbar"' in barre.group(0)
    assert "aria-hidden" not in barre.group(0)
    assert "aria-label" in barre.group(0)

    js = (STATIC / "app.js").read_text(encoding="utf-8")
    for attribut in ("aria-valuenow", "aria-valuemax", "aria-valuetext"):
        assert attribut in js, f"{attribut} n'est jamais posé : la barre annoncée resterait muette"


def test_plus_de_sur_titre_en_capitales_au_dessus_de_la_question():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    regle = re.search(r"\.challenge-step\s*\{([^}]*)\}", css)
    assert regle, "témoin : la règle du compteur doit exister"
    assert "uppercase" not in regle.group(1)

    js = (STATIC / "app.js").read_text(encoding="utf-8")
    ligne = [l for l in js.splitlines() if '$("challenge-step").textContent = `' in l]
    assert ligne, "témoin : le texte du compteur doit être posé"
    assert all("—" not in l for l in ligne), "tiret cadratin dans le compteur"
