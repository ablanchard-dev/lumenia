# -*- coding: utf-8 -*-
"""La page dit ce qui est enregistré. Elle ne disait pas qui peut le lire.

19/09/2026. La politique de confidentialité de Lumenia est soignée — plus que la
plupart. Elle nomme **exactement quatre tables**, un test tient cette exhaustivité
dans les deux sens, et elle va jusqu'à déclarer que l'anti-spam transforme l'adresse
IP en condensat salé. Sur le **quoi**, elle ne cache rien.

Elle ne répond jamais au **qui**.

MESURE : `/journal`, `/journal/export`, `/profile`, `/risk` et `/consent` sont des
lectures **GET sans aucune authentification**, et la page le dit elle-même ailleurs :
« Lumenia n'a pas de compte utilisateur ». Les deux faits mis bout à bout donnent une
conséquence que la page ne tire nulle part : **toute personne capable d'atteindre
l'instance lit ces entrées**. Il n'y a pas de « vos » notes au sens où quelqu'un
l'entend — il y a les notes de l'instance.

POURQUOI ÇA COMPTE ICI PLUS QU'AILLEURS. Le journal est l'objet le plus intime que ce
produit détient, et il s'adresse à des personnes qu'on invite explicitement à écrire
ce qui ne va pas. Quelqu'un qui lit « les notes que vous écrivez » sur une adresse
partagée avec un proche, un collègue ou une classe en déduira raisonnablement que
personne d'autre ne les voit. C'est faux, et ce n'est écrit nulle part.

CE N'EST PAS UNE DEMANDE DE COMPTES. L'absence de compte est une décision assumée et
déclarée. Ce qui manque n'est pas une fonctionnalité, c'est **une phrase** — et sans
elle, la page la plus honnête du produit laisse croire le contraire de ce qui est vrai.

Ce fichier déduit les lectures sans compte depuis le code, et exige que la page tire la
conséquence, à l'endroit où quelqu'un la lira : dans la section qui énumère ce que le
serveur enregistre.

23/09/2026 — LA CONSÉQUENCE A CHANGÉ, PAS LA QUESTION. Chaque lecture exige maintenant
l'identifiant aléatoire du navigateur (`Depends(visiteur)`, audit C-1) : un visiteur ne lit
plus les notes d'un autre. La phrase « toute personne capable d'atteindre l'instance lit ces
entrées » est devenue fausse — et ce fichier la garantissait. Il garantit désormais les deux
faits vrais : la cloison existe dans le CODE (chaque lecture passe par l'identifiant), et la
page dit QUI peut encore lire (l'administrateur de l'instance, et qui copierait l'identifiant).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MAIN = RACINE / "app" / "main.py"
MODELS = RACINE / "app" / "models.py"
PAGE = RACINE / "static" / "confidentialite.html"

# Les classes de tables, lues dans le code — jamais une liste tenue à la main.
def _tables() -> set[str]:
    arbre = ast.parse(MODELS.read_text(encoding="utf-8-sig"))
    return {
        n.name for n in ast.walk(arbre)
        if isinstance(n, ast.ClassDef)
        and any(isinstance(b, ast.Name) and b.id == "Base" for b in n.bases)
    }


def _lectures_sans_compte() -> list[str]:
    """Les routes GET dont le corps touche une table. Aucune n'exige d'identité."""
    source = MAIN.read_text(encoding="utf-8-sig")
    arbre = ast.parse(source)
    tables = _tables()

    routes: list[str] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in noeud.decorator_list:
            if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
                continue
            if deco.func.attr != "get" or not deco.args:
                continue
            chemin = getattr(deco.args[0], "value", None)
            if not isinstance(chemin, str):
                continue
            noms = {n.id for n in ast.walk(noeud) if isinstance(n, ast.Name)}
            if noms & tables:
                routes.append(chemin)
    return sorted(routes)


def _section_des_tables() -> str:
    """La section « Ce que le serveur enregistre », seule — pas la page entière."""
    html = PAGE.read_text(encoding="utf-8")
    debut = html.index("Ce que le serveur enregistre")
    fin = html.index("<section>", debut)
    return html[debut:fin]


def test_le_crible_trouve_bien_des_lectures_sans_compte():
    """Témoin : sans lui, un motif cassé rendrait tout le fichier vert sur du vide."""
    routes = _lectures_sans_compte()

    assert "/journal" in routes, routes
    assert len(routes) >= 3, routes


def test_chaque_lecture_passe_par_l_identifiant_du_navigateur():
    """Le fait mesuré, pas supposé : chaque route GET qui lit une table exige le visiteur."""
    arbre = ast.parse(MAIN.read_text(encoding="utf-8-sig"))
    routes = set(_lectures_sans_compte())
    sans_cloison = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.FunctionDef):
            continue
        chemins = {getattr(d.args[0], "value", None) for d in noeud.decorator_list
                   if isinstance(d, ast.Call) and d.args}
        if not chemins & routes:
            continue
        defauts = [ast.unparse(d) for d in noeud.args.defaults]
        if "Depends(visiteur)" not in defauts:
            sans_cloison.append(noeud.name)
    assert sans_cloison == [], f"ces lectures ne sont pas cloisonnées : {sans_cloison}"


def test_la_page_dit_QUI_peut_encore_lire():
    section = _section_des_tables().lower()

    assert "identifiant" in section, "la section doit dire ce qui cloisonne les entrées"
    assert "administre" in section, (
        "la cloison ne protège pas du fichier de la base : la page doit nommer qui peut "
        "encore tout lire"
    )
    assert "atteindre cette instance peut lire" not in section, (
        "phrase d'avant le 23/09, devenue fausse : un visiteur ne lit plus les notes d'un autre"
    )


def test_la_phrase_est_la_OU_on_lit_ce_qui_est_enregistre():
    """Contrepoids : enterrée trois sections plus bas, elle ne serait pas lue.

    La page est longue et bien écrite ; c'est précisément pour ça qu'un avertissement
    placé ailleurs que devant la liste des tables manque son lecteur.
    """
    html = PAGE.read_text(encoding="utf-8")
    section = _section_des_tables()

    assert "journal" in section, "la section des tables doit bien être celle-là"
    assert len(section) < len(html) / 2, "cette section ne doit pas être la page entière"


def test_la_page_ne_promet_JAMAIS_une_intimite_qu_elle_n_a_pas():
    """Second contrepoids, le plus important : ajouter une phrase vraie ne suffit pas
    si une autre, ailleurs, dit le contraire."""
    html = PAGE.read_text(encoding="utf-8").lower()

    for promesse in ("vous seul", "vous seule", "personne d'autre ne peut",
                     "nul autre", "vous êtes le seul"):
        assert promesse not in html, (
            f"« {promesse} » est faux : l'administrateur de l'instance lit la base, "
            "et quiconque copie l'identifiant lit ce qu'il protège"
        )
