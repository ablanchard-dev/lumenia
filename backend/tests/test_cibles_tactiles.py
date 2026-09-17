# -*- coding: utf-8 -*-
"""Sur un écran tactile, une commande doit être atteignable au doigt.

Mesuré dans un navigateur à 430 px le 17/09/2026, écran de chat ouvert :
`conv-del` (supprimer une conversation) faisait **30 × 30 px**, `safety-close`
36 × 36, `conv-open` 231 × 42, `sidebar-card-link` 237 × 32. Le seuil de
WCAG 2.5.5 et des recommandations Apple/Google est **44 × 44**.

Ce n'est pas un détail d'esthétique pour ce produit en particulier : Lumenia
s'adresse à des profils TDAH et autistes, où la précision motrice et la fatigue
attentionnelle sont justement ce qu'on ménage. Et la plus petite des cibles
était la **destructive**.

Le test lit la feuille : il ne remplace pas la mesure au navigateur, il empêche
qu'une valeur redescende sans que personne le voie.
"""
import re
from pathlib import Path

STYLE = Path(__file__).resolve().parent.parent / "static" / "style.css"
CSS = STYLE.read_text(encoding="utf-8")

SEUIL = 44
POINTUS = ["conv-del", "conv-open", "sidebar-card-link", "safety-close"]


def _bloc_tactile() -> str:
    """Le bloc @media dédié aux petits écrans où les cibles sont agrandies."""
    m = re.search(r"@media \(max-width: 760px\) \{(.*?)\n\}", CSS, re.S)
    assert m, "aucun bloc @media (max-width: 760px) pour les cibles tactiles"
    return m.group(1)


def test_chaque_commande_de_l_ecran_de_chat_fait_44px_sur_petit_ecran():
    bloc = _bloc_tactile()
    for nom in POINTUS:
        regle = re.search(rf"\.{nom}\s*\{{([^}}]*)\}}", bloc)
        assert regle, f".{nom} n'est pas agrandi sur petit écran"
        tailles = [int(v) for v in re.findall(r"(?:min-)?(?:width|height):\s*(\d+)px", regle.group(1))]
        assert tailles, f".{nom} ne déclare aucune taille"
        assert min(tailles) >= SEUIL, f".{nom} : {min(tailles)}px < {SEUIL}px"


def test_la_cible_destructive_est_carree_et_non_seulement_haute():
    """Une corbeille de 44 px de haut mais 30 de large reste ratée une fois sur deux."""
    regle = re.search(r"\.conv-del\s*\{([^}]*)\}", _bloc_tactile())
    contenu = regle.group(1)
    largeur = re.search(r"width:\s*(\d+)px", contenu)
    hauteur = re.search(r"height:\s*(\d+)px", contenu)
    assert largeur and hauteur, "conv-del doit fixer largeur ET hauteur"
    assert int(largeur.group(1)) >= SEUIL and int(hauteur.group(1)) >= SEUIL


def test_l_icone_ne_grossit_pas_avec_la_cible():
    """Agrandir la zone cliquable, pas le dessin : une corbeille de 44 px de haut
    dans une barre latérale basse, ce serait de la stimulation en plus."""
    assert ".conv-del svg { width: 15px; height: 15px; }" in CSS
