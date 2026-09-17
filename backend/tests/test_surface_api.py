# -*- coding: utf-8 -*-
"""La surface exposée doit rester celle qu'on a décidé d'exposer.

Mesure du 17/09/2026 : **dix routes de l'API ne sont appelées par aucune ligne
du front**, dont cinq qui appellent un modèle de langage — donc cinq portes
ouvertes sur le budget LLM de qui héberge Lumenia, pour une fonctionnalité que
personne ne peut déclencher depuis l'interface.

Ce fichier ne supprime rien : ce qui sort de l'API est une décision produit,
pas un nettoyage de passage. Il transforme une dérive silencieuse en dérive
visible : la liste est écrite ici, et toute route ajoutée sans consommateur fait
rougir la suite. Le jour où une de ces routes trouve son écran, elle quitte la
liste ; le jour où elle est retirée, elle la quitte aussi.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FRONT = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text(encoding="utf-8")

# Routes exposées que le front n'appelle pas, constatées le 17/09/2026.
# Les cinq premières atteignent un modèle : ce sont celles qui coûtent.
SANS_CONSOMMATEUR = {
    # Les cinq qui atteignent un modele : ce sont celles qui coutent.
    "/focus/decompose",
    "/impostor/reframe",
    "/creativity/generate",
    "/scenarios",
    "/psy/coach",
    # Les questionnaires cliniques (« legacy » selon le README).
    "/assessment/entry",
    "/assessment/phq9",
    "/assessment/gad7",
    # Et celles-ci, plus surprenantes : le journal et le profil sont ecrits,
    # exportables et lisibles par l'API, mais AUCUN ecran ne les appelle.
    "/journal",
    "/journal/export",
    "/profile",
    "/adapt",
    "/resources",        # les ressources de crise : le front code le 3114 en dur
    "/entry/challenge",  # une epreuve seule ; le front tire un parcours entier
}

# Ce qui est servi a un humain n'est pas « appele par le front » : c'est le front.
PAGES = {"/", "/cgu", "/confidentialite", "/robots.txt", "/sitemap.xml", "/healthz",
         # Ajoutee le 17/09 : le navigateur la demande seul, aucun ecran ne l'appelle,
         # et ce test l'a signalee des son ajout — c'est le garde-fou qui a fonctionne.
         "/favicon.ico"}


def _routes_exposees() -> set[str]:
    return {
        r.path for r in app.routes
        if getattr(r, "methods", None)
        and r.path not in ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect")
        and r.path not in PAGES
        and not r.path.startswith("/static")
    }


def _appelee_par_le_front(chemin: str) -> bool:
    return re.search(re.escape(chemin) + r'["\'?]', FRONT) is not None


def test_la_liste_des_routes_sans_consommateur_est_exacte():
    exposees = _routes_exposees()
    constatees = {r for r in exposees if not _appelee_par_le_front(r)}

    nouvelles = constatees - SANS_CONSOMMATEUR
    disparues = SANS_CONSOMMATEUR - constatees

    assert not nouvelles, (
        f"routes exposées que rien n'appelle et qui ne sont pas dans la liste : {sorted(nouvelles)}. "
        "Soit un écran les utilise, soit elles rejoignent la liste sciemment.")
    assert not disparues, (
        f"ces routes ont trouvé un consommateur ou ont été retirées : {sorted(disparues)}. "
        "Mettre la liste à jour — c'est une bonne nouvelle, pas un échec.")


def test_toutes_les_routes_qui_coutent_un_LLM_sont_limitees():
    """Une route sans écran reste une porte : elle doit au moins être rationnée."""
    from app import limite
    couteuses = {"/focus/decompose", "/impostor/reframe", "/creativity/generate",
                 "/scenarios", "/psy/coach", "/chat"}
    assert couteuses <= limite.ROUTES_LLM


def test_aucune_route_exposee_n_echappe_au_robots_txt():
    """Ce qui n'a pas d'écran n'a rien à faire dans un index de recherche."""
    robots = client.get("/robots.txt").text
    interdits = {l.split("Disallow:")[1].strip() for l in robots.splitlines() if l.startswith("Disallow:")}
    for route in _routes_exposees():
        assert any(route.startswith(i) for i in interdits), f"{route} n'est couverte par aucun Disallow"
