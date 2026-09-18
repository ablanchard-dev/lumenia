# -*- coding: utf-8 -*-
"""Ce que Lumenia garantit doit tenir aussi quand le serveur tombe.

18/09/2026. `test_web_quality.py` porte un test nommé « les en-têtes de sécurité
sont sur TOUTES les réponses ». Il dit vrai des réponses normales, et c'est là
que la phrase promet plus qu'elle ne prouve : mesuré aujourd'hui, une route qui
lève renvoie `Internal Server Error` en `text/plain`, **sans CSP, sans nosniff,
sans X-Frame-Options, sans Referrer-Policy**, et sans le 3114.

L'exception remonte au-dessus du middleware qui pose les en-têtes : ce n'est pas
un oubli de configuration, c'est l'ordre des couches.

Ce que ça coûte, dans l'ordre : une personne qui allait mal reçoit une page
d'erreur nue, sans le numéro qui est partout ailleurs dans le produit ; et la
réponse d'erreur est la seule du site à pouvoir être encadrée dans une iframe
ou interprétée de travers.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as principal

EN_TETES_ATTENDUS = (
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "x-frame-options",
)


@pytest.fixture
def route_cassee(monkeypatch):
    """Casse une vraie route, au lieu d'en inventer une qui ne prouverait rien."""
    def tombe(*args, **kwargs):
        raise RuntimeError("panne simulée dans le moteur d'entrée")

    monkeypatch.setattr(principal, "get_challenge", tombe)
    return TestClient(principal.app, raise_server_exceptions=False)


def test_le_temoin_la_route_repond_normalement_sans_la_panne():
    """Sans ce témoin, un test vert ne dirait pas si la panne a bien été simulée."""
    client = TestClient(principal.app)

    assert client.get("/entry/challenge").status_code == 200


def test_une_panne_reste_une_panne_declaree(route_cassee):
    reponse = route_cassee.get("/entry/challenge")

    assert reponse.status_code == 500, "une panne ne doit pas se déguiser en succès"
    assert "Traceback" not in reponse.text and "RuntimeError" not in reponse.text, (
        "le détail interne ne sort jamais vers le client"
    )


@pytest.mark.parametrize("entete", EN_TETES_ATTENDUS)
def test_les_en_tetes_de_securite_tiennent_aussi_quand_ca_casse(route_cassee, entete):
    reponse = route_cassee.get("/entry/challenge")

    assert reponse.headers.get(entete), (
        f"la réponse d'erreur part sans {entete} : c'est la seule page du site "
        "à ne pas être protégée, et c'est celle qui apparaît quand ça va mal"
    )


def test_la_panne_porte_le_3114_comme_le_reste_du_produit(route_cassee):
    """Le 3114 est sur tous les écrans et jusque dans la réponse 429 de l'anti-spam.
    Une panne ne doit pas être le seul endroit où il disparaît."""
    reponse = route_cassee.get("/entry/challenge")

    assert "3114" in reponse.text


def test_une_panne_sur_l_api_reste_du_json(route_cassee):
    """Le front lit du JSON : lui rendre du texte brut casse son affichage d'erreur."""
    reponse = route_cassee.get("/entry/challenge", headers={"accept": "application/json"})

    assert reponse.headers["content-type"].startswith("application/json")
    assert reponse.json()["error"]
