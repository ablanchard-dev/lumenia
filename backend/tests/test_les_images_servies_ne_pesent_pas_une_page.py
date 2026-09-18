# -*- coding: utf-8 -*-
"""Le poids réel de ce qu'un visiteur télécharge, image comprise.

18/09/2026. Le test de vitesse existant pèse le HTML, les polices et le script.
Les images, personne ne les pesait — et c'est là qu'était le défaut :
`logo-lumenia-cut.png` fait **2,18 Mo** en 1248×1254, et la page d'accueil le
déclare comme `apple-touch-icon`. Une icône. Sur un téléphone, « ajouter à
l'écran d'accueil » téléchargeait deux mégaoctets pour dessiner un carré de
180 points, et sur une connexion lente c'est de la bande passante prise à la
page elle-même.

Apple recommande 180×180 pour cette icône. Le fichier d'origine reste dans
`static/` : il sert d'illustration ailleurs, ce n'est pas lui le problème, c'est
son emploi comme icône.
"""
import re
import struct
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

RACINE = Path(__file__).resolve().parent.parent
client = TestClient(app)

# Une image de page, ce n'est pas un téléchargement : au-delà, elle prend la
# bande passante de la page qu'elle est censée décorer.
BUDGET_PAR_IMAGE = 200 * 1024

# Recommandation Apple pour `apple-touch-icon` : une icône carrée de 180 points.
COTE_ICONE_TACTILE = 180


def _pages_publiques() -> list[str]:
    plan = client.get("/sitemap.xml")
    return sorted(
        {re.sub(r"^https?://[^/]+", "", url) or "/" for url in re.findall(r"<loc>([^<]+)</loc>", plan.text)}
    )


def _images_reclamees() -> dict[str, set[str]]:
    """Chaque image que le HTML public fait charger : <img>, <link rel=icon…>."""
    trouvees: dict[str, set[str]] = {}
    motif = re.compile(r'(?:src|href)="(/static/[^"]+\.(?:png|jpe?g|webp|gif|svg))"', re.I)
    for page in _pages_publiques():
        for cible in motif.findall(client.get(page).text):
            trouvees.setdefault(cible, set()).add(page)
    return trouvees


def _cote_png(octets: bytes) -> tuple[int, int]:
    """Largeur et hauteur lues dans le bloc IHDR, sans dépendance externe."""
    assert octets[:8] == b"\x89PNG\r\n\x1a\n", "ce n'est pas un PNG"
    return struct.unpack(">II", octets[16:24])


def test_le_crible_voit_bien_les_images_de_la_page():
    """Témoin : un motif cassé rendrait le test du poids vert sur le vide."""
    images = _images_reclamees()

    assert len(images) >= 2, images
    assert any(c.endswith(".svg") for c in images), "le logo vectoriel a disparu du HTML"


def test_aucune_image_de_page_ne_pese_plus_qu_une_page():
    reclamees = _images_reclamees()
    # Temoin de non-vacuite : ce crible LIT les pages pour trouver leurs images. Le jour ou
    # le motif ne mord plus -- un attribut ecrit autrement, un chemin change -- il ne trouve
    # rien, la boucle ne tourne pas, et le budget par image n'est plus garde par personne.
    assert len(reclamees) > 0, "aucune image reclamee par les pages : le crible ne lit plus rien"

    lourdes = {}
    for cible, pages in reclamees.items():
        reponse = client.get(cible)
        assert reponse.status_code == 200, f"{cible} est réclamée par {sorted(pages)} et ne se sert pas"
        if len(reponse.content) > BUDGET_PAR_IMAGE:
            lourdes[cible] = f"{len(reponse.content) // 1024} Ko (budget {BUDGET_PAR_IMAGE // 1024})"

    assert lourdes == {}, f"ces images prennent la bande passante de la page : {lourdes}"


def test_l_icone_tactile_fait_la_taille_de_l_icone_tactile():
    """Une icône servie en 1248 points coûte l'image entière pour dessiner 180."""
    html = client.get("/").text
    declaree = re.search(r'<link[^>]+rel="apple-touch-icon"[^>]+href="([^"]+)"', html)
    assert declaree, "la page d'accueil ne déclare plus d'icône tactile"

    fichier = client.get(declaree.group(1))
    assert fichier.status_code == 200

    assert _cote_png(fichier.content) == (COTE_ICONE_TACTILE, COTE_ICONE_TACTILE)


def test_le_crible_sait_mesurer_un_png():
    """Témoin inverse : sans ce repère, un décodage faux rendrait le test muet."""
    grand = (RACINE / "static" / "logo-lumenia-cut.png").read_bytes()

    assert _cote_png(grand) == (1248, 1254)
    assert len(grand) > BUDGET_PAR_IMAGE, "l'image d'origine est bien celle qu'on ne sert pas en icône"
