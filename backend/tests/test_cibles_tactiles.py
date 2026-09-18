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
# 18/09/2026 : « safety-close » a quitté cette liste, et c'est le correctif, pas un
# relâchement. Le bouton n'a JAMAIS porté cette classe (id=safety-close,
# class=btn-icon) : en l'exigeant comme sélecteur de classe, ce test validait une
# règle morte et laissait le bouton de la bannière de crise à 36 × 36. Il est
# désormais couvert par un test dédié qui vise un sélecteur l'atteignant vraiment.
POINTUS = ["conv-del", "conv-open", "sidebar-card-link"]


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


# -----------------------------------------------------------------------------
# 18/09/2026 — bannière de crise ouverte pour la première fois (message de détresse
# envoyé dans le chat, base jetable). Tout y est bon : role="alert", contrastes
# 14,57 et 6,45, le 3114 et le 15 à 44 px de haut.
#
# Sauf le bouton qui la ferme : **36 × 36**. La règle censée l'agrandir existe
# pourtant dans le bloc tactile — elle vise `.safety-close`, une CLASSE, alors que
# le bouton porte `class="btn-icon"` et `id="safety-close"`. Elle ne s'applique à
# rien, et `.safety-banner .btn-icon { width: 36px }` gagne sans opposition.
#
# Une regle CSS peut nommer une garantie sans la tenir, exactement comme un test.
# Ce que ces tests figent : la regle vise ce qu'elle pretend viser.
# -----------------------------------------------------------------------------

SOURCES = "".join(
    (STYLE.parent / f).read_text(encoding="utf-8") for f in ("index.html", "app.js")
)

# Les classes REELLEMENT posees quelque part : celles qui apparaissent dans un
# attribut `class="..."`, que le balisage soit ecrit dans la page ou fabrique par
# le script (la liste des conversations l'est entierement).
CLASSES_POSEES = {
    mot
    # `class="a b"` dans le balisage écrit…
    for attribut in re.findall(r'class="([^"]*)"', SOURCES)
       # …et `el.className = "a b"` dans le script, qui construit toute la liste
       # des conversations. Ignorer la seconde forme ferait crier ce garde sur
       # trois classes parfaitement saines — et un garde qui crie au loup finit
       # désactivé, ce qui coûte plus cher que le défaut qu'il cherchait.
       + re.findall(r'className\s*=\s*"([^"]*)"', SOURCES)
    for mot in attribut.split()
}


def test_le_bouton_qui_ferme_la_banniere_de_crise_est_une_vraie_cible():
    bloc = _bloc_tactile()
    regle = re.search(r"(?:#safety-close|\.safety-banner\s+\.btn-icon)\s*\{([^}]*)\}", bloc)
    assert regle, (
        "aucune regle du bloc tactile ne vise le bouton de fermeture par un selecteur "
        "qui l'atteint (il porte id=safety-close et class=btn-icon)")
    tailles = [int(v) for v in re.findall(r"(?:min-)?(?:width|height):\s*(\d+)px", regle.group(1))]
    assert len(tailles) >= 2, f"largeur ET hauteur attendues : {regle.group(1)}"
    assert min(tailles) >= SEUIL, f"{min(tailles)}px < {SEUIL}px"


def test_aucune_regle_tactile_ne_vise_une_classe_absente_du_html():
    """Le temoin de la classe de defaut : une regle qui ne matche rien est pire
    qu'une regle absente, parce qu'elle donne l'impression que c'est traite."""
    mortes = sorted(
        classe
        for classe in set(re.findall(r"\.([a-z][\w-]*)\s*\{", _bloc_tactile()))
        if classe not in CLASSES_POSEES
    )
    assert mortes == [], f"regles tactiles qui ne visent aucun element : {mortes}"
