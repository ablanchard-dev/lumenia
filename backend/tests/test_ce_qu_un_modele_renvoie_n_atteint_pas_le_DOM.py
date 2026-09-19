# -*- coding: utf-8 -*-
"""Le texte d'un modèle distant devient du HTML. Rien ne le vérifiait.

19/09/2026. Une réponse de modèle arrive du réseau et finit dans
`body.innerHTML = renderMarkdown(text)`. C'est le seul endroit du produit où une
chaîne venue d'ailleurs devient du **balisage** plutôt que du texte.

Le rendu est bien écrit : il échappe d'abord, puis réintroduit une liste blanche
minuscule — gras, italique, listes. Aucun attribut n'est fabriqué, aucun lien.
Après lecture et après exécution, **je n'y ai trouvé aucun défaut**. Ce tour n'est
donc pas une correction, c'est la garde qui manquait.

Ce qui la rendait nécessaire : la sûreté de ce rendu était affirmée par un
commentaire — « Mini-rendu markdown sûr » — et par rien d'autre. Aucun test ne
l'exécutait. Le jour où quelqu'un ajoute les liens markdown (la demande la plus
naturelle du monde sur un rendu de chat), `inline()` fabriquera un `href`, et
`escapeHtml` n'échappe **ni les guillemets ni les apostrophes** : l'attribut sera
le premier endroit où une réponse de modèle pourra sortir de son texte. Ce jour-là,
ce fichier rougit.

🔑 CE TEST EXÉCUTE, IL NE RELIT PAS. Les deux fonctions sont extraites de
`static/app.js` — le fichier réellement servi — et lancées dans Node sur des charges
hostiles. Un crible qui cherche des motifs dans du JavaScript se fait battre par la
première ligne qu'il n'a pas prévue ; une exécution répond sur le vrai code.

Pourquoi ça compte sur CE produit : la personne en face est en difficulté, elle a
accepté de parler à cette interface, et le fournisseur du modèle est un tiers gratuit
enchaîné avec d'autres. « Le modèle ne renverra pas de balisage hostile » n'est pas
une garantie qu'on tient, c'est un espoir.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parent.parent / "static" / "app.js"
SOURCE = APP_JS.read_text(encoding="utf-8")

# Ce qu'un modèle — ou un fournisseur compromis — peut renvoyer.
CHARGES = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '<iframe src="https://exemple.invalide"></iframe>',
    "- <img src=x onerror=alert(1)>",
    "**gras** puis <script>alert(1)</script>",
    '<a href="javascript:alert(1)">cliquez ici</a>',
    "\" onmouseover=\"alert(1)",
    "<svg/onload=alert(1)>",
    # 🔴 CELLE-CI MANQUAIT, et c'est la seule qui décrit ce que ce fichier PROMET.
    # L'en-tête annonce qu'il rougira le jour où quelqu'un ajoutera les liens markdown.
    # Mutation faite : liens ajoutés dans `inline()` → les douze tests sont restés VERTS.
    # Toutes mes charges étaient du HTML brut, que l'échappement neutralise avant même
    # d'arriver à `inline()`. Aucune n'employait la syntaxe markdown — c'est-à-dire la
    # seule porte que le rendu ouvre volontairement. Le fichier nommait une garantie
    # qu'il ne tenait pas.
    "[cliquez ici](javascript:alert(1))",
    "[normal](https://exemple.invalide)",
]

# Les SEULES balises que ce rendu a le droit de fabriquer.
#
# 🔴 Première version : une liste de sous-chaînes interdites (« onerror », « src= »,
# « <img »…). Elle accusait le rendu SAIN : une charge échappée sort en
# `&lt;img src=x onerror=…&gt;`, du texte parfaitement inoffensif qui contient
# quand même ces mots. Un crible qui rougit sur la bonne réponse ne prouve rien —
# il apprend seulement à être désactivé. Ce qui compte n'est pas le mot, c'est la
# BALISE réellement produite.
BALISES_AUTORISEES = {"p", "/p", "ul", "/ul", "ol", "/ol", "li", "/li",
                      "strong", "/strong", "em", "/em"}


def _fonctions_de_rendu() -> str:
    """Le code RÉELLEMENT servi, extrait du fichier livré — jamais recopié ici."""
    debut = SOURCE.index("function escapeHtml")
    fin = SOURCE.index("/* ---------------- thème", debut)
    return SOURCE[debut:fin]


def _rendre(entrees: list[str]) -> list[str]:
    programme = (
        _fonctions_de_rendu()
        + "\nconst entrees = JSON.parse(process.argv[1]);\n"
        + "console.log(JSON.stringify(entrees.map(renderMarkdown)));\n"
    )
    sortie = subprocess.run(
        ["node", "-e", programme, json.dumps(entrees)],
        capture_output=True, text=True, timeout=60,
    )
    assert sortie.returncode == 0, sortie.stderr
    return json.loads(sortie.stdout)


@pytest.fixture(scope="module", autouse=True)
def _node_present():
    if shutil.which("node") is None:
        pytest.skip("Node absent : ce fichier EXÉCUTE le rendu, il ne le relit pas")


def test_le_crible_extrait_bien_le_code_servi():
    """Témoin : sans lui, une extraction cassée rendrait tout vert sur du vide."""
    code = _fonctions_de_rendu()

    assert "function escapeHtml" in code
    assert "function renderMarkdown" in code
    assert "innerHTML = renderMarkdown(" in SOURCE, (
        "si ce rendu n'alimente plus le DOM, ce fichier surveille autre chose"
    )


def _balises(rendu: str) -> list[str]:
    """Les balises réellement produites, telles quelles."""
    return [b.strip("<>").strip() for b in re.findall(r"<[^>]*>", rendu)]


@pytest.mark.parametrize("charge", CHARGES)
def test_aucune_charge_hostile_ne_ressort_en_balisage(charge):
    rendu = _rendre([charge])[0]

    intruses = [b for b in _balises(rendu) if b.lower() not in BALISES_AUTORISEES]

    assert intruses == [], (
        f"{charge!r} a produit les balises {intruses} — rendu : {rendu!r}"
    )


def test_les_chevrons_ressortent_ECHAPPES_pas_supprimes():
    """La personne doit lire ce que le modèle a écrit, même quand c'est du balisage.

    Contrepoids : « supprimer tout ce qui ressemble à du HTML » serait sûr et
    mensonger — le texte affiché ne serait plus celui de la réponse.
    """
    rendu = _rendre(["<script>alert(1)</script>"])[0]

    assert "&lt;script&gt;" in rendu
    assert "alert(1)" in rendu, "le texte reste lisible, c'est le balisage qui tombe"


def test_le_gras_et_les_listes_marchent_toujours():
    """Second contrepoids : la sûreté ne doit pas se payer en écran illisible.

    Un correctif qui échapperait aussi les étoiles rendrait tous les tests
    précédents verts — et transformerait chaque réponse structurée en pavé.
    """
    gras, liste = _rendre(["**important**", "- premier\n- second"])

    assert "<strong>important</strong>" in gras
    assert gras.count("<strong>") == 1
    assert liste.count("<li>") == 2


def test_aucun_ATTRIBUT_n_est_fabrique_a_partir_du_texte():
    """La porte par laquelle ça cassera un jour.

    `escapeHtml` n'échappe ni `"` ni `'`. Tant que le rendu ne fabrique aucun
    attribut, c'est sans conséquence. Le jour où quelqu'un ajoute les liens
    markdown, ce test rougit AVANT que la réponse d'un modèle ne porte un `href`.
    """
    entrees = [
        'guillemet " et apostrophe \' au milieu',
        # La syntaxe markdown est la seule porte que le rendu ouvre volontairement :
        # c'est par là qu'un attribut apparaîtra, pas par du HTML brut déjà échappé.
        '[lien](https://exemple.invalide)',
        '[piège](javascript:alert(1))',
    ]
    rendus = _rendre(entrees)

    assert '"' in rendus[0], "le témoin : le guillemet doit bien traverser le rendu"

    for balise in re.findall(r"<[^>]+>", "".join(rendus)):
        assert "=" not in balise, (
            f"{balise} porte un attribut : `escapeHtml` ne protège pas les guillemets, "
            "donc un attribut construit à partir du texte d'un modèle est une sortie"
        )
