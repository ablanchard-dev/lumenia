# -*- coding: utf-8 -*-
"""Une icône décorative doit se taire pour un lecteur d'écran.

Mesuré le 18/09/2026 sur les pages servies : les `<img>` portent toutes leur `alt`
(vide sur le logo, qui double le nom écrit juste à côté — décoratif légitime), et
il y a bien **un seul appel à l'action par écran**.

Mais **13 `<svg>` n'étaient ni masqués ni étiquetés**. Un SVG laissé nu est parcouru
par les lecteurs d'écran : selon le lecteur, il annonce « graphique », lit le
contenu du `<title>` s'il y en a un, ou s'arrête dessus à la tabulation. Pour un
produit qui s'adresse à des profils autistes et TDAH — dont beaucoup utilisent la
synthèse vocale et pour qui le bruit coûte cher — c'est exactement ce qu'on est
censé leur épargner.

La règle figée ici : tout `<svg>` est **soit masqué** (`aria-hidden="true"`, cas de
l'icône qui double un texte déjà présent), **soit étiqueté** (`role="img"` +
`aria-label`, cas de l'icône qui porte à elle seule une information).
"""
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "static"
# `app.js` figure dans cette liste, et c'est le correctif de ma première version :
# elle ne lisait que le balisage ÉCRIT, se déclarait verte, et le navigateur voyait
# quand même **15 svg dont un nu** — la corbeille d'une conversation, construite par
# le script. Un crible ne voit que là où il regarde ; celui-ci regardait à côté.
PAGES = ["index.html", "cgu.html", "confidentialite.html", "404.html", "app.js"]

BALISE_SVG = re.compile(r"<svg\b([^>]*)>")


def _svg_nus(html: str):
    nus = []
    for attributs in BALISE_SVG.findall(html):
        masque = 'aria-hidden="true"' in attributs
        etiquete = 'role="img"' in attributs and "aria-label=" in attributs
        if not (masque or etiquete):
            classe = re.search(r'class="([^"]*)"', attributs)
            nus.append(classe.group(1) if classe else "(sans classe)")
    return nus


@pytest.mark.parametrize("page", PAGES)
def test_chaque_svg_est_masque_ou_etiquete(page):
    html = (STATIC / page).read_text(encoding="utf-8")
    nus = _svg_nus(html)
    assert nus == [], f"{page} : {len(nus)} svg ni masqués ni étiquetés → {nus}"


def test_le_crible_voit_bien_des_svg():
    """Témoin : sur une page sans le moindre `<svg>`, le test précédent passerait
    en annonçant une garantie qu'il n'a jamais exercée."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert len(BALISE_SVG.findall(html)) >= 10


def test_le_crible_attraperait_une_icone_nue():
    """Témoin inverse : le motif doit rougir sur un svg laissé nu."""
    assert _svg_nus('<svg class="test"><path/></svg>') == ["test"]
    assert _svg_nus('<svg aria-hidden="true"></svg>') == []
    assert _svg_nus('<svg role="img" aria-label="Lune"></svg>') == []


@pytest.mark.parametrize("page", PAGES)
def test_chaque_image_porte_un_texte_alternatif(page):
    """`alt=""` est permis — c'est la façon correcte de dire « décoratif » — mais
    l'attribut absent, lui, laisse le lecteur lire le nom du fichier."""
    html = (STATIC / page).read_text(encoding="utf-8")
    sans_alt = [i for i in re.findall(r"<img\b[^>]*>", html) if not re.search(r"\salt\s*=", i)]
    assert sans_alt == [], f"{page} : {sans_alt}"
