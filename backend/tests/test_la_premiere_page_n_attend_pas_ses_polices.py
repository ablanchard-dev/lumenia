# -*- coding: utf-8 -*-
"""La première page attend ses polices un aller-retour de trop.

19/09/2026. Les polices sont servies par nous depuis le 17/09 — plus aucun appel à
Google. C'est la bonne décision, et elle a un effet de bord que personne n'a mesuré :
un navigateur ne **découvre** un fichier de police qu'après avoir téléchargé la
feuille de style, l'avoir analysée, puis avoir trouvé du texte qui l'emploie. Trois
étapes avant la première requête, alors que le HTML, lui, est déjà là.

CE QUE ÇA DONNE À L'ÉCRAN. `font-display: swap` — le bon réglage, il évite le texte
invisible — fait peindre le texte dans la police de repli, puis **rebasculer** quand
la vraie arrive. Sur ce produit, le premier écran est le mot-marque « Lumenia » en
Lora, animé, au centre d'un fond sombre. Le voir apparaître en Georgia puis changer
de forme, c'est exactement la secousse qu'un design annoncé **low-stim** ne veut pas.

MESURE : `lora-latin.woff2` pèse 37 Ko et `raleway-latin.woff2` 48 Ko. Les deux sont
employés dès le premier écran (le mot-marque, puis la signature). Aucune des pages ne
les précharge.

LES DEUX AUTRES NE DOIVENT PAS L'ÊTRE. `lora-latin-ext` (20 Ko) et
`raleway-latin-ext` (31 Ko) sont déclarés avec un `unicode-range` : le navigateur ne
les télécharge **que** si la page contient ces caractères. Les précharger imposerait
51 Ko à tout le monde pour des signes que presque personne n'affiche — l'inverse du
but.

⚠️ LE PIÈGE DU PRÉCHARGEMENT, et c'est celui qu'on rate. Une police se télécharge
toujours en mode CORS, **même depuis son propre domaine**. Un `preload` sans
`crossorigin` ne correspond donc pas à la requête que fera `@font-face` : le fichier
est téléchargé **deux fois**, et la page devient plus lente qu'avant le correctif.
Même piège si l'URL préchargée n'est pas exactement celle du `src` : ce fichier-ci
est testé contre la feuille de style, jamais contre une liste écrite à la main.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
STATIC = Path(__file__).resolve().parent.parent / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")

# Les deux sous-ensembles employés par le premier écran, sans condition d'alphabet.
CRITIQUES = ("/static/polices/lora-latin.woff2", "/static/polices/raleway-latin.woff2")

# Ceux que `unicode-range` rend conditionnels : les précharger coûterait à tout le monde.
CONDITIONNELS = ("/static/polices/lora-latin-ext.woff2", "/static/polices/raleway-latin-ext.woff2")


def _preloads(html: str) -> list[str]:
    """Les balises `<link rel="preload">` de la page, telles quelles."""
    return [b for b in re.findall(r"<link\b[^>]*>", html) if 'rel="preload"' in b]


def _url(balise: str) -> str:
    m = re.search(r'href="([^"]+)"', balise)
    return m.group(1) if m else ""


def _sources_du_css() -> set[str]:
    """Les URL que `@font-face` demande vraiment."""
    return set(re.findall(r"src:\s*url\('([^']+)'\)", CSS))


def test_le_crible_lit_bien_la_feuille_et_la_page():
    """Témoin : sans lui, un chemin changé rendrait tout le reste vert sur du vide."""
    assert len(_sources_du_css()) >= 4, _sources_du_css()
    assert "font-display: swap" in CSS
    assert client.get("/").status_code == 200


def test_les_polices_du_PREMIER_ecran_sont_prechargees():
    html = client.get("/").text
    prechargees = {_url(b) for b in _preloads(html)}

    manquantes = [u for u in CRITIQUES if u not in prechargees]

    assert manquantes == [], (
        "le navigateur ne découvre ces fichiers qu'après avoir analysé la feuille de style : "
        f"le mot-marque s'affiche en police de repli, puis change de forme — {manquantes}"
    )


def test_aucune_police_CONDITIONNELLE_n_est_imposee_a_tout_le_monde():
    """Contrepoids : précharger, c'est décider de télécharger. 51 Ko pour presque personne."""
    prechargees = {_url(b) for b in _preloads(client.get("/").text)}

    imposees = [u for u in CONDITIONNELS if u in prechargees]

    assert imposees == [], (
        "`unicode-range` rend ces fichiers conditionnels : les précharger les impose à "
        f"toutes les visites, y compris celles qui n'en affichent aucun caractère — {imposees}"
    )


def test_chaque_prechargement_porte_crossorigin():
    """Le piège : sans lui, la police est téléchargée DEUX fois.

    Une police se télécharge toujours en mode CORS, même depuis son propre domaine. Un
    préchargement sans `crossorigin` ne correspond pas à la requête de `@font-face` — le
    navigateur en fait une seconde, et la page devient plus lente qu'avant le correctif.
    """
    for balise in _preloads(client.get("/").text):
        if _url(balise).endswith(".woff2"):
            assert "crossorigin" in balise, balise
            assert 'as="font"' in balise, balise
            assert 'type="font/woff2"' in balise, balise


def test_l_url_prechargee_est_EXACTEMENT_celle_que_le_CSS_demande():
    """Second contrepoids, même conséquence : une URL qui diverge télécharge deux fois."""
    sources = _sources_du_css()

    for balise in _preloads(client.get("/").text):
        url = _url(balise)
        if url.endswith(".woff2"):
            assert url in sources, (
                f"{url} n'est demandé par aucun `@font-face` : ce préchargement est soit un "
                "fichier mort, soit un second téléchargement du même texte"
            )


def test_chaque_fichier_precharge_repond_vraiment():
    """Un préchargement vers une adresse morte est une requête perdue et un avertissement."""
    # Témoin : une boucle sur une collection vide affirme tout et ne prouve rien. Le crible
    # de non-vacuité du dépôt a pris ce test-ci avant moi — il a fait son travail sur son
    # auteur, comme au tour 121.
    verifies = 0

    for balise in _preloads(client.get("/").text):
        url = _url(balise)
        if url.endswith(".woff2"):
            r = client.get(url)

            assert r.status_code == 200, (url, r.status_code)
            assert r.headers["content-type"] == "font/woff2", url
            verifies += 1

    assert verifies == len(CRITIQUES), verifies
