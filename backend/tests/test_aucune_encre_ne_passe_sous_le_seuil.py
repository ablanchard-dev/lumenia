# -*- coding: utf-8 -*-
"""Toutes les encres de la feuille de style, pas seulement celles qu'on a listées.

18/09/2026. `test_contraste.py` mesure trois couples écrits à la main : l'encre du
bouton sur son dégradé, le texte courant et le texte atténué sur le fond. C'est
juste, et c'est incomplet — une liste tenue à la main prend du retard sur le CSS.

Mesure du jour : elle avait déjà pris du retard. `--accent` sert de couleur de
texte à trois endroits (le « bonne réponse » des épreuves, le lien de la carte
latérale, l'icône de la bannière de sécurité) et, **en thème clair**, il donne
3,51:1 sur le fond de page là où WCAG AA demande 4,5:1 pour du texte.

Le crible ci-dessous relit le CSS : toute variable employée dans une déclaration
`color:` doit être mesurée ici, contre les fonds sur lesquels elle est vraiment
posée. Le lien encre → fonds est déclaré à la main ; le deviner reviendrait à
accuser l'encre du bouton de ne pas se lire sur le fond de page, où elle n'est
jamais posée.
"""
import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parent.parent / "static" / "style.css").read_text(encoding="utf-8")

AA_TEXTE_NORMAL = 4.5

THEMES = (":root", '[data-theme="light"]')

# Les fonds de page : ce sur quoi le texte courant est posé.
FONDS_DE_PAGE = ("bg", "surface", "surface-2")

# Chaque encre employée en `color:`, avec les fonds où elle apparaît vraiment.
ENCRES = {
    "text": FONDS_DE_PAGE,
    "text-muted": FONDS_DE_PAGE,
    "accent": FONDS_DE_PAGE,
    "danger": FONDS_DE_PAGE,
    "primary": FONDS_DE_PAGE,
    # L'encre du bouton ne vit que sur le bouton : son dégradé, pas la page.
    "on-primary": ("primary", "primary-strong"),
}


def _srgb(canal: float) -> float:
    canal /= 255
    return canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4


def luminance(hexa: str) -> float:
    h = hexa.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def bloc(selecteur: str) -> str:
    m = re.search(re.escape(selecteur) + r"\s*\{(.*?)\}", CSS, re.S)
    assert m, f"bloc {selecteur} introuvable"
    return m.group(1)


def token(nom: str, b: str) -> str:
    m = re.search(rf"--{nom}:\s*(#[0-9a-fA-F]{{3,8}})\s*;", b)
    assert m, f"token --{nom} introuvable dans ce thème"
    return m.group(1)


def _encres_du_css() -> set[str]:
    """Les variables employées comme couleur de texte, lues dans la feuille."""
    return set(re.findall(r"(?<!-)\bcolor:\s*var\(--([a-z0-9-]+)\)", CSS))


def test_le_crible_voit_bien_des_encres_dans_la_feuille():
    """Témoin : un motif cassé rendrait le test suivant vert sur le vide."""
    encres = _encres_du_css()

    assert len(encres) >= 4, encres
    assert "text" in encres


def test_aucune_encre_de_la_feuille_n_echappe_a_la_mesure():
    """La leçon de la liste tenue à la main : elle prend du retard sur le CSS."""
    oubliees = sorted(_encres_du_css() - set(ENCRES))

    assert oubliees == [], (
        "ces couleurs de texte ne sont mesurées nulle part : ajoutez-les avec les fonds "
        f"sur lesquels elles sont réellement posées — {oubliees}"
    )


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("encre", sorted(ENCRES))
def test_chaque_encre_se_lit_sur_ses_fonds(theme, encre):
    b = bloc(theme)
    valeur = token(encre, b)

    fautes = [
        f"--{encre} ({valeur}) sur --{fond} ({token(fond, b)}) : {ratio(valeur, token(fond, b)):.2f}:1"
        for fond in ENCRES[encre]
        if ratio(valeur, token(fond, b)) < AA_TEXTE_NORMAL
    ]

    assert fautes == [], f"{theme} — {fautes}"


def test_le_calcul_est_lui_meme_verifie():
    """Sans ces deux repères, le fichier n'est qu'une opinion chiffrée."""
    assert round(ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(ratio("#777777", "#ffffff"), 2) == 4.48
