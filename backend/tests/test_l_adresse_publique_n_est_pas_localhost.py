# -*- coding: utf-8 -*-
"""Déployé tel quel, le site annonce `localhost` au monde entier.

18/09/2026. `web.py` s'ouvre sur cette phrase :

    « `PUBLIC_ORIGIN` decide de l'adresse publique, et un sitemap qui annonce
      localhost est un sitemap faux »

La phrase est juste. Mesure du jour : **rien ne définit `PUBLIC_ORIGIN`**. Pas le
README, pas `docker-compose.yml`, pas un `.env.example`, pas le `Dockerfile` — la
variable n'existe que dans `web.py` et dans deux tests qui la posent eux-mêmes
avec `monkeypatch`. Un déploiement réel prend donc le défaut :
`http://localhost:8000`, et le sert dans **tout** ce qui parle de l'adresse du
site : `<link rel="canonical">`, `og:url`, `og:image`, et le `Sitemap:` de
`robots.txt`.

Ce que ça coûte, le code le dit déjà ailleurs : « sans ces balises, Lumenia est
une ligne grise dans une conversation ». Une `og:image` sur localhost est
introuvable pour tout le monde sauf la machine qui sert.

**Le correctif ne consiste pas à documenter la variable.** Une configuration
qu'il faut penser à poser est une configuration qu'on oublie — et ici l'oubli est
silencieux, tout répond 200. Le produit sait déjà à quelle adresse on lui parle :
l'en-tête `Host` de la requête. `PUBLIC_ORIGIN` reste ce qui fait autorité quand
il est posé (derrière un proxy, c'est lui qui sait), mais sans lui, l'origine se
déduit de la requête au lieu d'être inventée.
"""
from fastapi.testclient import TestClient

from app import web
from app.main import app

client = TestClient(app)

DOMAINE = "lumenia.example"


def test_le_crible_lit_bien_une_page_et_un_robots(monkeypatch):
    """Témoin : sans lui, une route cassée rendrait tout vert sur du vide."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)

    page = client.get("/")
    robots = client.get("/robots.txt")

    assert page.status_code == 200 and 'rel="canonical"' in page.text
    assert "Sitemap:" in robots.text


def test_sans_configuration_le_site_n_annonce_pas_localhost(monkeypatch):
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)

    page = client.get("/", headers={"host": DOMAINE})

    assert "localhost" not in page.text, (
        "la page servie sur un vrai domaine annonce localhost dans son canonical, son og:url "
        "et son og:image. Personne d'autre que la machine qui sert ne peut atteindre ces "
        "adresses : le lien partagé devient une ligne grise"
    )
    assert DOMAINE in page.text, "l'adresse annoncée doit être celle à laquelle on a demandé la page"


def test_le_plan_du_site_suit_la_meme_adresse(monkeypatch):
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)

    robots = client.get("/robots.txt", headers={"host": DOMAINE})
    sitemap = client.get("/sitemap.xml", headers={"host": DOMAINE})

    assert "localhost" not in robots.text, "un sitemap qui annonce localhost est un sitemap faux"
    assert "localhost" not in sitemap.text
    assert DOMAINE in robots.text and DOMAINE in sitemap.text


def test_la_variable_reste_ce_qui_fait_autorite(monkeypatch):
    """L'autre sens : derrière un proxy, c'est la configuration qui sait, pas l'en-tête."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://lumenia.fr")

    page = client.get("/", headers={"host": "interne.reseau.local"})

    assert "https://lumenia.fr/" in page.text
    assert "interne.reseau.local" not in page.text, (
        "quand PUBLIC_ORIGIN est posé, l'en-tête Host ne doit pas le contredire — sinon "
        "n'importe quel client choisit ce que la page déclare être"
    )


def test_en_local_rien_ne_change(monkeypatch):
    """Le poste de développement continue de s'annoncer comme lui-même."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)

    page = client.get("/", headers={"host": "localhost:8000"})

    assert "http://localhost:8000/" in page.text
    assert web.public_origin() == "http://localhost:8000", "le défaut hors requête ne bouge pas"
