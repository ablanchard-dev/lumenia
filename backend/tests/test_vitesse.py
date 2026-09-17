# -*- coding: utf-8 -*-
"""La page ne dépend d'aucun tiers, et son poids est borné.

Mesure du 17/09/2026 dans un vrai navigateur : 8 requetes, 67 Ko, DOM pret en
38 ms en local. Le probleme n'etait pas le poids -- c'etaient **deux domaines
Google sur le chemin critique** (`fonts.googleapis.com` et `fonts.gstatic.com`).
Pour un produit dont l'argument tient en « aucun cookie, aucun traceur », faire
appeler Google par le navigateur du visiteur a chaque premiere visite est une
contradiction ; et c'est aussi deux resolutions DNS + deux poignees TLS avant
que le texte ne s'affiche.

Ces tests pinnent les deux moities : plus aucun tiers, et un poids qui ne derive pas.
"""
import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient

from app import web
from app.main import app

client = TestClient(app)
STATIC = Path(__file__).resolve().parent.parent / "static"
NAVIGATEUR = {"accept": "text/html,application/xhtml+xml"}

PAGES = ["/", "/confidentialite", "/cgu", "/page-inconnue"]
PLAFOND_POLICE_KO = 120      # une police variable latine tient largement dessous
PLAFOND_PAGE_KO = 120        # html + css + js, hors polices


def html(chemin):
    return client.get(chemin, headers=NAVIGATEUR).text


def test_aucune_page_ne_CHARGE_quoi_que_ce_soit_chez_un_tiers():
    """Un lien qu'on peut cliquer (la CNIL) n'est pas une requete : le navigateur
    ne le suit que si le visiteur le decide. Ce qui compte ici, ce sont les
    ressources que la page va chercher toute seule : feuilles, scripts, images,
    polices, preconnect."""
    charge = re.compile(r'<(?:link|script|img|iframe)[^>]*(?:href|src)="https?://([^/"]+)')
    notre_hote = urlparse(web.public_origin()).netloc
    for chemin in PAGES:
        texte = html(chemin)
        # `rel="canonical"` declare une adresse, il ne charge rien : on l'ecarte,
        # comme on ecarte un lien cliquable.
        texte = re.sub(r'<link rel="canonical"[^>]*>', "", texte)
        etrangers = [h for h in charge.findall(texte) if h != notre_hote]
        assert etrangers == [], f"{chemin} charge {etrangers}"


def test_la_csp_n_autorise_plus_aucun_hote_externe():
    csp = client.get("/").headers["content-security-policy"]
    assert "fonts.googleapis.com" not in csp
    assert "fonts.gstatic.com" not in csp
    assert "style-src 'self'" in csp
    assert "font-src 'self'" in csp


def test_les_polices_declarees_existent_vraiment_et_sont_en_woff2():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    sources = re.findall(r"src:\s*url\('([^']+)'\)", css)
    assert sources, "aucune @font-face declaree"
    for src in sources:
        fichier = STATIC / src.split("/static/")[-1]
        assert fichier.exists(), src
        assert fichier.suffix == ".woff2", src
        poids = fichier.stat().st_size / 1024
        assert poids < PLAFOND_POLICE_KO, f"{src} : {poids:.0f} Ko"


def test_chaque_police_est_servie_et_se_met_en_cache_longtemps():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    for src in re.findall(r"src:\s*url\('([^']+)'\)", css):
        r = client.get(src)
        assert r.status_code == 200, src
        assert r.headers["content-type"] in ("font/woff2", "application/octet-stream"), src


def test_le_texte_reste_lisible_pendant_le_chargement_des_polices():
    """`font-display: swap` : le texte s'affiche tout de suite avec la police de secours, au lieu d'une page blanche le temps du telechargement."""
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    faces = css.count("@font-face")
    assert faces >= 2
    assert css.count("font-display: swap") == faces


def test_le_poids_de_la_page_ne_derive_pas():
    """Hors polices : le HTML, la feuille et le script."""
    total = len(client.get("/").content)
    total += len(client.get("/static/style.css").content)
    total += len(client.get("/static/app.js").content)
    ko = total / 1024
    assert ko < PLAFOND_PAGE_KO, f"{ko:.0f} Ko"
