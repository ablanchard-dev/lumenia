# -*- coding: utf-8 -*-
"""Deux angles morts du même genre : quelque chose n'était borné, ou pas regardé.

1. `/assessment/entry` acceptait **n'importe quel dictionnaire**. Mesuré le
   17/09/2026 : 5 000 clés de 999999, et une clé de 5 000 caractères, acceptées
   et écrites en base (200). Le parcours d'entrée compte six dimensions.
   On borne la TAILLE, pas le sens : je ne connais pas la liste légitime des
   clés de cette route héritée, donc je ne l'invente pas.

2. La garde « aucune page ne charge chez un tiers » (tour 8) ne regardait que
   les quatre pages servies par une route. `intro-preview.html` et `logo-lab.html`
   vivent dans `static/`, sont servis par le montage `/static`, et appelaient
   toujours Google Fonts. Même forme d'angle mort que la garde DrDXT d'hier :
   le motif était bon, la **portée** était trop étroite.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
STATIC = Path(__file__).resolve().parent.parent / "static"


# ---------------- 1. la taille de /assessment/entry ----------------
def test_un_dictionnaire_demesure_est_refuse():
    enorme = {f"k{i}": 1 for i in range(5_000)}
    assert client.post("/assessment/entry", json={"answers": enorme}).status_code == 422


def test_une_cle_demesuree_est_refusee():
    assert client.post(
        "/assessment/entry", json={"answers": {"x" * 5_000: 1}}).status_code == 422


def test_un_parcours_de_taille_normale_passe():
    """Le témoin : six dimensions, c'est ce que le parcours produit vraiment."""
    reel = {"verbal": 4, "fluide": 5, "memoire": 3, "visuo": 4, "vitesse": 5, "libre": 1}
    r = client.post("/assessment/entry", json={"answers": reel})
    assert r.status_code == 200
    assert r.json()["total"] == 22


# ---------------- 2. la portée de la garde « aucun tiers » ----------------
def test_AUCUN_fichier_html_de_static_n_appelle_un_tiers():
    """Y compris ceux qu'aucune route ne sert : `/static` les sert quand même,
    et une page d'atelier reste une page qu'un navigateur peut ouvrir."""
    charge = re.compile(r'<(?:link|script|img|iframe)[^>]*(?:href|src)="https?://([^/"]+)')
    fautifs = {}
    for page in sorted(STATIC.glob("*.html")):
        hotes = charge.findall(page.read_text(encoding="utf-8"))
        if hotes:
            fautifs[page.name] = sorted(set(hotes))
    assert fautifs == {}, fautifs


def test_les_pages_d_atelier_sont_bien_servies_donc_bien_concernees():
    """Sans ce test, quelqu'un pourrait croire que ces fichiers sont hors ligne."""
    for nom in ("intro-preview.html", "logo-lab.html"):
        assert client.get(f"/static/{nom}").status_code == 200, nom
