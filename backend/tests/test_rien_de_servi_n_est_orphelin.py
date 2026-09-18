# -*- coding: utf-8 -*-
"""Ce que le serveur expose doit être ce qu'on a décidé d'exposer.

18/09/2026, symétrique du tour 92 sur l'autre dépôt : là-bas, 2,0 Mo d'images
étaient compilées dans l'exécutable sans qu'aucun écran ne les affiche. Ici, la
même question donne une réponse pire, parce que `StaticFiles` monte **tout le
dossier** : les fichiers orphelins ne sont pas seulement du poids, ils sont
**publiquement atteignables**.

Mesure du 18/09, quatre orphelins, tous servis en 200 :

    /static/logo-lab.html       8,5 Ko   « Lumenia — cinq pistes de logo »
    /static/intro-preview.html  1,6 Ko   « intro animée (démo) »
    /static/og-card.html        1,1 Ko   la source qui a servi à rendre og-image.jpg
    /static/logo-lumenia-cut.png 2,13 Mo référencé par aucune page

Trois planches de travail internes, sans `<title>` produit, sans le 3114, sans
mention légale — et `robots.txt` ne disait rien de `/static` : un moteur pouvait
les indexer et les faire remonter à côté du vrai site, sur une application de
santé mentale.

Ce test ne supprime rien : retirer un fichier est une décision d'Alex. Il exige
que chaque page servie soit soit un écran du produit, soit un atelier **déclaré**
— et, dans ce cas, refusé aux robots.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
STATIC = Path(__file__).resolve().parent.parent / "static"

# Les pages du produit : servies par une route, avec leur titre et leurs metas.
ECRANS = {"index.html", "cgu.html", "confidentialite.html", "404.html", "500.html"}

# Les planches de travail internes. Gardées sciemment, en attendant qu'Alex
# tranche ; la raison est ce qu'on relira le jour où l'une remontera dans Google.
ATELIERS = {
    "logo-lab.html": "cinq pistes de logo — planche de design, jamais un ecran du produit",
    "intro-preview.html": "demo de l'intro animee",
    "og-card.html": "la source qui a servi a rendre og-image.jpg",
}

# Fichiers lourds : au-dela de ce seuil, etre orphelin coute vraiment quelque chose.
SEUIL_LOURD_KO = 500

POIDS_ACCEPTE = {
    "logo-lumenia-cut.png": "2,13 Mo, reference par aucune page — garder ou retirer est une decision d'Alex",
}


def _pages_servies() -> str:
    """Le texte de tout ce que le produit sert vraiment à un humain."""
    return "\n".join((STATIC / n).read_text(encoding="utf-8") for n in sorted(ECRANS))


def test_le_crible_lit_bien_le_dossier_servi():
    """Témoin : sans lui, un dossier déplacé rendrait tout vert sur du vide."""
    html = {f.name for f in STATIC.glob("*.html")}

    assert ECRANS <= html, f"un ecran du produit a disparu : {ECRANS - html}"
    assert len(list(STATIC.iterdir())) > 5


def test_chaque_page_servie_est_un_ecran_ou_un_atelier_declare():
    inconnues = sorted(f.name for f in STATIC.glob("*.html") if f.name not in ECRANS | set(ATELIERS))

    assert inconnues == [], (
        f"ces pages sont servies publiquement et ne sont ni un ecran du produit ni un atelier "
        f"declare : {inconnues}. `StaticFiles` monte tout le dossier — deposer un fichier ici, "
        "c'est le publier"
    )


def test_aucun_atelier_n_est_laisse_aux_moteurs():
    robots = client.get("/robots.txt").text

    oublies = sorted(nom for nom in ATELIERS if f"/static/{nom}" not in robots)

    assert oublies == [], (
        f"ces planches de travail sont indexables : {oublies}. Sans titre produit, sans le 3114 "
        "et sans mention legale, une planche de logos qui remonte a cote du vrai site sur une "
        "application de sante mentale n'est pas un detail de referencement"
    )


def test_aucun_fichier_lourd_n_est_servi_sans_raison():
    lourds = [f for f in STATIC.iterdir() if f.is_file() and f.stat().st_size > SEUIL_LOURD_KO * 1024]
    servies = _pages_servies()

    orphelins = sorted(f.name for f in lourds if f.name not in servies and f.name not in POIDS_ACCEPTE)

    assert orphelins == [], (
        f"ces fichiers depassent {SEUIL_LOURD_KO} Ko, sont servis publiquement, et aucune page "
        f"du produit ne les reference : {orphelins}"
    )


def test_la_liste_des_exceptions_ne_vieillit_pas():
    """L'autre sens : une exception qui n'a plus lieu d'etre doit sortir de la liste."""
    servies = _pages_servies()
    presents = {f.name for f in STATIC.iterdir()}

    perimees = sorted(
        nom for nom in set(ATELIERS) | set(POIDS_ACCEPTE)
        if nom not in presents or nom in servies
    )

    assert perimees == [], (
        f"ces exceptions ne decrivent plus le depot : {perimees} — le fichier a ete retire, ou "
        "une page l'utilise enfin. Une liste d'exceptions qui vieillit finit par decrire un "
        "produit qui n'existe plus"
    )
