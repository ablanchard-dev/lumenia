# -*- coding: utf-8 -*-
"""Ce que la page raconte d'elle-meme : au moteur de recherche, et au lien partage.

Un titre nu (`Lumenia`) ne dit rien a qui ne connait pas deja. Et un lien colle
dans une conversation sans `og:` est une ligne grise que personne n'ouvre.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
NAVIGATEUR = {"accept": "text/html,application/xhtml+xml"}


def page(chemin="/", **kw):
    return client.get(chemin, headers=NAVIGATEUR, **kw).text


def test_le_titre_dit_ce_que_c_est_et_pour_qui():
    html = page()
    titre = html.split("<title>")[1].split("</title>")[0]
    assert titre != "Lumenia", "un titre nu ne dit rien a qui ne connait pas deja"
    assert len(titre) <= 65, f"{len(titre)} caracteres : Google coupe vers 60"
    assert "Lumenia" in titre


def test_la_description_tient_dans_ce_qui_est_affiche():
    html = page()
    desc = html.split('name="description" content="')[1].split('"')[0]
    assert 70 <= len(desc) <= 160, f"{len(desc)} caracteres"


def test_le_lien_partage_porte_un_titre_une_description_et_une_image():
    html = page()
    for balise in ("og:title", "og:description", "og:image", "og:type", "og:url"):
        assert f'property="{balise}"' in html, balise
    assert 'name="twitter:card" content="summary_large_image"' in html


def test_l_image_du_lien_partage_existe_vraiment_et_a_la_bonne_forme():
    """Une og:image qui rend 404 est pire que pas d'image du tout."""
    html = page()
    src = html.split('property="og:image" content="')[1].split('"')[0]
    assert src.startswith("http"), "og:image doit etre une URL absolue"
    chemin = "/" + src.split("/", 3)[3]
    r = client.get(chemin)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    # 1200x630 : la taille que Facebook, LinkedIn et X recadrent sans rogner.
    assert _taille_jpeg(r.content) == (1200, 630)
    # Une carte de partage lourde ralentit la page qui la reference : elle reste
    # sous 200 Ko. Le meme visuel en PNG pesait 274 Ko, mesure.
    assert len(r.content) < 200_000, f"{len(r.content) // 1024} Ko"


def _taille_jpeg(octets: bytes):
    """Largeur/hauteur lues dans le marqueur SOF du JPEG."""
    i = 2
    while i < len(octets):
        if octets[i] != 0xFF:
            i += 1
            continue
        marqueur = octets[i + 1]
        if 0xC0 <= marqueur <= 0xCF and marqueur not in (0xC4, 0xC8, 0xCC):
            hauteur = int.from_bytes(octets[i + 5:i + 7], "big")
            largeur = int.from_bytes(octets[i + 7:i + 9], "big")
            return largeur, hauteur
        i += 2 + int.from_bytes(octets[i + 2:i + 4], "big")
    raise AssertionError("pas un JPEG lisible")


def test_les_url_absolues_suivent_l_origine_publique(monkeypatch):
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://lumenia.example")
    html = page()
    assert "https://lumenia.example/static/og-image.jpg" in html
    assert "{{ORIGIN}}" not in html


def test_la_page_404_reste_hors_des_index():
    html = page("/inconnu")
    assert 'name="robots" content="noindex' in html
