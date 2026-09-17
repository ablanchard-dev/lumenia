# -*- coding: utf-8 -*-
"""Le contraste du texte, calcule sur la feuille de style, pas juge a l'oeil.

Trouve le 17/09 en mesurant la page dans un navigateur : `.btn-primary` codait
`#fff` en dur sur le degrade violet. Ratio 2,7:1 la ou WCAG AA demande 4,5:1 --
et c'est le bouton principal de TOUS les ecrans (« Entrer dans le seuil »,
« Continuer »), pas une decoration.

Ce test relit les couleurs dans `style.css` : il retombe en echec si quelqu'un
reintroduit une couleur de texte qui ne se lit pas sur son fond.
"""
import re
from pathlib import Path

STYLE = Path(__file__).resolve().parent.parent / "static" / "style.css"
CSS = STYLE.read_text(encoding="utf-8")

AA_TEXTE_NORMAL = 4.5


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


def token(nom: str, bloc: str) -> str:
    """Valeur d'une variable CSS dans un bloc (:root ou [data-theme=light])."""
    m = re.search(rf"--{nom}:\s*(#[0-9a-fA-F]{{3,8}})\s*;", bloc)
    assert m, f"token --{nom} introuvable"
    return m.group(1)


def bloc(selecteur: str) -> str:
    m = re.search(re.escape(selecteur) + r"\s*\{(.*?)\}", CSS, re.S)
    assert m, f"bloc {selecteur} introuvable"
    return m.group(1)


def test_le_ratio_est_bien_calcule():
    """Un calcul qu'on ne verifie pas est une opinion : deux valeurs connues."""
    assert round(ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(ratio("#777777", "#ffffff"), 2) == 4.48  # le gris pivot de WCAG


def test_le_bouton_principal_ne_code_aucune_couleur_en_dur():
    """Une couleur en dur echappe aux deux themes : elle doit passer par un token."""
    regle = bloc(".btn-primary")
    m = re.search(r"(?<!-)\bcolor:\s*([^;]+);", regle)
    assert m, ".btn-primary ne declare pas de couleur de texte"
    assert "var(--on-primary)" in m.group(1), (
        f".btn-primary code '{m.group(1).strip()}' au lieu du token --on-primary")


def test_le_texte_du_bouton_se_lit_aux_DEUX_bouts_du_degrade():
    """Le fond est un degrade : le bas est plus sombre que le haut, il decide."""
    for theme in (":root", '[data-theme="light"]'):
        b = bloc(theme)
        encre = token("on-primary", b)
        for fond in ("primary", "primary-strong"):
            r = ratio(encre, token(fond, b))
            assert r >= AA_TEXTE_NORMAL, f"{theme} {encre} sur --{fond} : {r:.2f}:1"


def test_le_texte_courant_et_le_texte_attenue_se_lisent_sur_le_fond():
    for theme in (":root", '[data-theme="light"]'):
        b = bloc(theme)
        fond = token("bg", b)
        for encre in ("text", "text-muted"):
            r = ratio(token(encre, b), fond)
            assert r >= AA_TEXTE_NORMAL, f"{theme} --{encre} sur --bg : {r:.2f}:1"
