# -*- coding: utf-8 -*-
"""Une constante déclarée des deux côtés doit valoir la même chose des deux côtés.

18/09/2026. `app/entry.py` porte, au-dessus du seuil d'entrée :

    # Source de vérité SERVEUR (le front a sa propre constante
    # ENTRY_PASS_RATIO ; les deux doivent rester alignées).

La phrase promet. Rien ne la tenait — ni test, ni génération, ni import : deux
littéraux, dans deux langages, tenus alignés à la main.

**Ce que coûte une divergence**, et pourquoi elle ne se verrait pas :

* front plus strict que le serveur — quelqu'un qui a réussi selon le serveur lit
  « le seuil reste fermé » sur un test cognitif, alors que le chat lui est ouvert.
  Sur une application destinée à des personnes neuroatypiques, c'est un échec
  annoncé à tort ;
* front plus laxiste — l'écran annonce la réussite, puis `/chat` répond « termine
  le parcours ». La personne a réussi et l'application la renvoie au test.

Dans les deux cas, rien ne lève : les deux moitiés fonctionnent, elles ne sont
simplement pas d'accord.

Ce chiffre n'est pas un réglage : 0.85 et la longueur de 30 viennent du protocole
clinique de Blandine. Le laisser diverger, c'est laisser le front décider d'un
seuil clinique.

Le crible ne nomme pas `ENTRY_PASS_RATIO` : il compare **toutes** les constantes
que les deux côtés déclarent. Une deuxième duplication ajoutée demain entre
d'elle-même dans le garde — trois tests nominatifs ne disent jamais rien de la
quatrième surface.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

CONST_JS = re.compile(r"^\s*const\s+([A-Z][A-Z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;", re.M)
CONST_PY = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.M)


def _constantes_front() -> dict[str, float]:
    source = (BACKEND / "static" / "app.js").read_text(encoding="utf-8-sig")
    return {nom: float(v) for nom, v in CONST_JS.findall(source)}


def _constantes_serveur() -> dict[str, float]:
    trouvees: dict[str, float] = {}
    for fichier in sorted((BACKEND / "app").glob("*.py")):
        for nom, v in CONST_PY.findall(fichier.read_text(encoding="utf-8-sig")):
            trouvees[nom] = float(v)
    return trouvees


def _communes() -> list[str]:
    return sorted(set(_constantes_front()) & set(_constantes_serveur()))


def test_le_crible_voit_bien_une_constante_declaree_des_deux_cotes():
    """Témoin de contenu : sans lui, un motif cassé rendrait le garde vert sur du vide."""
    communes = _communes()

    assert communes, {
        "front": sorted(_constantes_front()),
        "serveur": sorted(_constantes_serveur()),
    }
    assert "ENTRY_PASS_RATIO" in communes, communes


def test_les_extracteurs_lisent_une_valeur_et_pas_n_importe_quoi():
    """Témoin inverse : deux extracteurs qui rendent toujours vide seraient verts."""
    assert CONST_JS.findall("  const ENTRY_PASS_RATIO = 0.85;") == [("ENTRY_PASS_RATIO", "0.85")]
    assert CONST_PY.findall("ENTRY_PASS_RATIO = 0.85") == [("ENTRY_PASS_RATIO", "0.85")]
    assert not CONST_JS.findall("  let seuil = 0.85;"), "une variable mutable n'est pas une constante"
    assert not CONST_PY.findall("_DRAW_DEFAULT = 6"), "le nom privé n'est pas une constante partagée"


def test_chaque_constante_partagee_vaut_la_meme_chose_des_deux_cotes():
    front, serveur = _constantes_front(), _constantes_serveur()

    desaccords = {
        nom: {"front": front[nom], "serveur": serveur[nom]}
        for nom in _communes()
        if front[nom] != serveur[nom]
    }

    assert desaccords == {}, (
        f"le front et le serveur ne comptent pas pareil : {desaccords}. Les deux moitiés "
        "fonctionnent, elles ne sont simplement pas d'accord — donc rien ne lève. Selon le "
        "sens de l'écart, quelqu'un lit « le seuil reste fermé » alors que le chat lui est "
        "ouvert, ou lit « réussi » puis se fait renvoyer au test"
    )
