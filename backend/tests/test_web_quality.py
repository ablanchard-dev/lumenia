# -*- coding: utf-8 -*-
"""Ce qu'un site doit tenir, verifie par requete et non par relecture.

Chaque test ici pin un point de la liste : il echoue le jour ou quelqu'un
retire la garantie sans s'en rendre compte. Les points qui demandent un oeil
(contraste, images, un seul CTA) ne sont pas ici : ils ne se prouvent pas
avec un client HTTP.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------- robots.txt et sitemap ----------------
def test_robots_txt_est_servi_et_designe_le_sitemap():
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "User-agent: *" in body
    assert "Sitemap:" in body
    # L'API n'a rien a faire dans un index de recherche.
    assert "Disallow: /chat" in body


def test_sitemap_xml_liste_au_moins_la_page_d_accueil():
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    assert "<urlset" in r.text
    assert "<loc>" in r.text


def test_le_sitemap_suit_l_origine_publique_declaree(monkeypatch):
    """Un sitemap qui annonce localhost est un sitemap faux en production."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://lumenia.example")
    r = client.get("/sitemap.xml")
    assert "https://lumenia.example/" in r.text
    assert "localhost" not in r.text


# ---------------- 404 ----------------
_NAVIGATEUR = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


def test_une_page_inconnue_rend_une_vraie_page_et_pas_du_json():
    """L'en-tete est celui qu'un vrai navigateur envoie : c'est lui qui decide."""
    r = client.get("/cette-page-n-existe-pas", headers=_NAVIGATEUR)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert "404" in r.text
    assert "3114" in r.text  # la page d'erreur reste une page de soin


def test_un_client_sans_preference_recoit_du_json():
    """curl, un script, un moniteur : `*/*` n'est pas un navigateur."""
    r = client.get("/cette-page-n-existe-pas")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


def test_une_route_d_api_inconnue_rend_toujours_du_json():
    """Le 404 humain ne doit pas casser un client d'API."""
    r = client.get("/journal/inconnu", headers={"accept": "application/json"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


# ---------------- en-tetes de securite ----------------
def test_les_en_tetes_de_securite_sont_sur_toutes_les_reponses():
    for path in ("/", "/healthz", "/robots.txt"):
        h = client.get(path).headers
        assert h["strict-transport-security"].startswith("max-age=")
        assert h["x-content-type-options"] == "nosniff"
        assert h["referrer-policy"] == "strict-origin-when-cross-origin"
        assert h["x-frame-options"] == "DENY"
        assert "default-src 'self'" in h["content-security-policy"]


def test_la_csp_autorise_exactement_les_polices_que_la_page_charge():
    csp = client.get("/").headers["content-security-policy"]
    assert "https://fonts.googleapis.com" in csp   # la feuille
    assert "https://fonts.gstatic.com" in csp      # les fichiers de police
    assert "frame-ancestors 'none'" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]


def test_https_force_seulement_quand_l_hebergeur_le_demande(monkeypatch):
    monkeypatch.setenv("FORCE_HTTPS", "1")
    r = client.get("/healthz", headers={"x-forwarded-proto": "http"}, follow_redirects=False)
    assert r.status_code == 308
    assert r.headers["location"].startswith("https://")


def test_sans_force_https_le_developpement_local_n_est_pas_redirige(monkeypatch):
    monkeypatch.delenv("FORCE_HTTPS", raising=False)
    r = client.get("/healthz", follow_redirects=False)
    assert r.status_code == 200


# ---------------- zero cookie ----------------
def test_aucune_reponse_ne_pose_de_cookie():
    """Alex a banni les cookies : c'est vrai aujourd'hui, ce test l'oblige a le rester."""
    for path in ("/", "/healthz", "/resources", "/robots.txt", "/sitemap.xml"):
        r = client.get(path)
        assert "set-cookie" not in {k.lower() for k in r.headers.keys()}, path
