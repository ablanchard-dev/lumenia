# -*- coding: utf-8 -*-
"""Une route LLM oubliée est une porte ouverte — et les deux gardes la cherchaient à la main.

Ce dépôt a déjà payé la leçon, le 17/09 : « je veux mourir, aide moi » envoyé à
`/focus/decompose` partait au LLM et revenait en décomposition de tâche, **sans le 3114**.
Cinq routes étaient concernées. La correction a listé ces cinq routes à la main, à deux
endroits :

  - `app/limite.py`   → `ROUTES_LLM`, l'ensemble rationné (le quota, le porte-monnaie) ;
  - `tests/test_crisis_all_routes.py` → `ROUTES`, l'ensemble où la détresse est testée.

🔴 Les deux sont des listes ÉCRITES. Une sixième route ajoutée demain n'entre dans aucune
des deux, et **les deux gardes restent vertes** : ni rationnée, ni testée pour la crise.
C'est exactement le défaut qu'elles avaient été écrites pour fermer, déplacé d'un cran.

Ce fichier ne lit aucune liste : il DÉDUIT les routes qui atteignent le LLM en lisant
`app/main.py`, et confronte ce que le code fait à ce que les deux listes prétendent.
"""
from __future__ import annotations

import ast
from pathlib import Path

from app import limite

MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"

# Les fonctions dont l'appel signifie « ce texte part chez un modèle ». `chat_reply` vient
# de `.chat` et non de `.llm`, mais elle appelle le modèle : la frontière est l'APPEL au
# LLM, pas le module qui l'héberge.
APPELS_LLM = {"decompose", "reframe", "creative", "scenarios", "psycho_coach", "chat_reply"}


def routes_llm_deduites(source: str) -> set[str]:
    """Les chemins des routes POST dont le corps appelle le LLM, lus dans le code."""
    arbre = ast.parse(source)
    trouvees: set[str] = set()

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        chemin = None
        for deco in noeud.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            cible = deco.func
            if not (isinstance(cible, ast.Attribute) and cible.attr == "post"):
                continue
            if deco.args and isinstance(deco.args[0], ast.Constant):
                chemin = deco.args[0].value
        if chemin is None:
            continue

        for sous in ast.walk(noeud):
            if isinstance(sous, ast.Call):
                f = sous.func
                nom = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                if nom in APPELS_LLM:
                    trouvees.add(chemin)
                    break

    return trouvees


def routes_du_test_de_crise() -> set[str]:
    """Les chemins listés dans `ROUTES` de `test_crisis_all_routes.py`, lus sans importer.

    Lu et pas importé : le paquet `tests` entre en collision avec un `tests` installé dans
    l'environnement, et surtout importer un module de test pour en tester un autre attache
    ce garde à ses effets de bord. Ici on ne veut que la liste.
    """
    fichier = Path(__file__).resolve().parent / "test_crisis_all_routes.py"
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Assign) and any(
            isinstance(c, ast.Name) and c.id == "ROUTES" for c in noeud.targets
        ):
            return {
                e.elts[0].value
                for e in noeud.value.elts
                if isinstance(e, ast.Tuple) and isinstance(e.elts[0], ast.Constant)
            }
    raise AssertionError("ROUTES introuvable dans test_crisis_all_routes.py")


def test_toute_route_qui_appelle_le_LLM_est_rationnee():
    """Sans ça, une boucle sur la route neuve vide le quota de qui héberge Lumenia."""
    deduites = routes_llm_deduites(MAIN.read_text(encoding="utf-8"))

    assert deduites, "le garde ne déduit plus aucune route : il ne garde plus rien"
    oubliees = deduites - limite.ROUTES_LLM
    assert not oubliees, (
        "ces routes appellent le LLM et ne sont pas dans limite.ROUTES_LLM : " + repr(sorted(oubliees))
    )


def test_toute_route_qui_appelle_le_LLM_est_couverte_par_le_test_de_crise():
    """Et sans ça, une détresse envoyée à la route neuve repart en réponse ordinaire.

    C'est la moitié qui compte : le quota est une affaire d'argent, la crise est une
    affaire de personne.
    """
    deduites = routes_llm_deduites(MAIN.read_text(encoding="utf-8"))
    couvertes = routes_du_test_de_crise() | {"/chat"}  # /chat a ses propres tests de crise

    non_couvertes = deduites - couvertes
    assert not non_couvertes, (
        "ces routes appellent le LLM et aucun test de crise ne les vise : "
        + repr(sorted(non_couvertes))
    )


def test_le_garde_VOIT_une_sixieme_route_ajoutee():
    """Un garde qu'on ne peut pas faire tomber sur commande ne prouve rien.

    Sans ce test, les deux du dessus prouveraient surtout que la déduction ne trouve rien.
    """
    faux = (
        "from .llm import decompose\n"
        "\n"
        "@app.post('/routine/plan')\n"
        "def routine_plan(body: PlanIn):\n"
        "    return {'plan': decompose(body.task)}\n"
    )

    deduites = routes_llm_deduites(faux)

    assert deduites == {"/routine/plan"}
    assert deduites - limite.ROUTES_LLM == {"/routine/plan"}, (
        "la route neuve doit ressortir comme non rationnée"
    )


def test_une_route_sans_LLM_n_est_pas_accusee():
    """Le contrepoids : `/consent` ou `/journal` ne coûtent rien et ne doivent rien déclencher.

    Sans lui, on aurait pu tout marquer comme route LLM et croire le garde satisfait.
    """
    faux = (
        "@app.post('/consent')\n"
        "def set_consent(accepted: bool):\n"
        "    return {'accepted': accepted}\n"
    )

    assert routes_llm_deduites(faux) == set()


# ---------------------------------------------------------------------------
# 18/09/2026 — LA DÉDUCTION CI-DESSUS S'ARRÊTE AU PREMIER CRAN.
#
# Elle lit le corps des routes de `main.py` et y cherche six noms écrits à la main
# (`APPELS_LLM`). Une route qui appelle une fonction qui, elle, appelle le modèle
# passe dessous sans être vue. C'est le cas mesuré ce jour :
#
#     POST /entry/verify → entry.verify_challenge → llm._chat
#
# Sept routes atteignent le modèle, six étaient rationnées. La septième tombait dans
# le budget des ÉCRITURES (120/min, calibré sur le disque) : six fois le plafond de
# conversation, pour un appel qui coûte exactement pareil.
#
# Ce qui suit ne cherche plus des noms : il construit le graphe d'appels de tout
# `app/`, marque les fonctions qui atteignent `_chat` **à n'importe quelle profondeur**,
# et remonte aux routes. Le garde du dessus reste : il tient la moitié « crise », qui
# ne concerne que les routes rendant du texte de modèle à la personne.
# ---------------------------------------------------------------------------

APP = MAIN.parent
POINT_D_ENTREE_LLM = "_chat"


def _fonctions_de(source: str) -> dict[str, set[str]]:
    """Pour chaque fonction du module : les noms qu'elle appelle."""
    arbre = ast.parse(source)
    appels: dict[str, set[str]] = {}
    for noeud in ast.walk(arbre):
        if isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            noms = set()
            for sous in ast.walk(noeud):
                if isinstance(sous, ast.Call):
                    f = sous.func
                    nom = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                    if nom:
                        noms.add(nom)
            appels[noeud.name] = noms
    return appels


def fonctions_qui_atteignent_le_modele() -> set[str]:
    """Clôture transitive : tout ce dont l'appel finit chez `_chat`, où qu'il soit."""
    appels: dict[str, set[str]] = {}
    # utf-8-sig et pas utf-8 : `app/models.py` porte un BOM. Python l'accepte a
    # l'import, `ast.parse` non -- le garde tombait sur une SyntaxError au lieu de lire.
    for fichier in sorted(APP.glob("*.py")):
        for nom, cibles in _fonctions_de(fichier.read_text(encoding="utf-8-sig")).items():
            appels.setdefault(nom, set()).update(cibles)

    atteignent = {POINT_D_ENTREE_LLM}
    change = True
    while change:  # petit graphe : le point fixe converge en quelques tours
        change = False
        for nom, cibles in appels.items():
            if nom not in atteignent and (cibles & atteignent):
                atteignent.add(nom)
                change = True
    return atteignent


def _routes_par(noms: set[str]) -> set[str]:
    """Les routes POST de `main.py` dont le corps appelle l'un de ces noms."""
    arbre = ast.parse(MAIN.read_text(encoding="utf-8"))
    trouvees: set[str] = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        chemin = None
        for deco in noeud.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) \
               and deco.func.attr == "post" and deco.args and isinstance(deco.args[0], ast.Constant):
                chemin = deco.args[0].value
        if chemin is None:
            continue
        for sous in ast.walk(noeud):
            if isinstance(sous, ast.Call):
                f = sous.func
                nom = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                if nom in noms:
                    trouvees.add(chemin)
                    break
    return trouvees


def routes_qui_atteignent_le_modele() -> set[str]:
    return routes_llm_deduites(MAIN.read_text(encoding="utf-8")) | _routes_par(
        fonctions_qui_atteignent_le_modele()
    )


def test_la_deduction_profonde_voit_ce_que_la_deduction_plate_manquait():
    """Témoin : sans lui, le test du dessous serait vert sur une déduction aveugle."""
    profondes = routes_qui_atteignent_le_modele()
    plates = routes_llm_deduites(MAIN.read_text(encoding="utf-8"))

    assert "/entry/verify" in profondes, (
        "le juge du parcours d'entrée part bien chez le modèle, deux crans sous la route"
    )
    assert "/entry/verify" not in plates, (
        "et la déduction plate ne pouvait pas le voir : c'est tout l'objet de celle-ci"
    )


def test_toute_route_qui_ATTEINT_le_LLM_est_rationnee_quelque_part():
    """Le plafond peut être ailleurs que dans le middleware — mais il doit exister."""
    non_rationnees = (
        routes_qui_atteignent_le_modele()
        - limite.ROUTES_LLM
        - limite.ROUTES_LLM_RATIONNEES_AILLEURS
    )
    assert not non_rationnees, (
        "ces routes atteignent le modèle et aucun plafond ne les couvre : "
        + repr(sorted(non_rationnees))
    )


def test_ce_qui_est_declare_rationne_ailleurs_l_est_vraiment():
    """Une dérogation qu'on n'aurait plus qu'à écrire ne garderait plus rien.

    `/entry/verify` est couvert par le plafond GLOBAL du juge : on le prouve ici en
    épuisant ce plafond, pas en lisant une liste.
    """
    assert limite.ROUTES_LLM_RATIONNEES_AILLEURS == {"/entry/verify"}, (
        "toute nouvelle dérogation doit venir avec sa preuve d'exécution"
    )

    limite.reset()
    assert limite.juge_autorise() is True
    for _ in range(limite.PAR_MINUTE_JUGE - 2):
        limite.juge_autorise()
    assert limite.juge_autorise() is True, "l'avant-dernier passage doit encore ouvrir"
    assert limite.juge_autorise() is False, "et le plafond doit bel et bien fermer"
    limite.reset()
