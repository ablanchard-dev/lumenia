# -*- coding: utf-8 -*-
"""La CI doit tester la version de Python qu'on livre, pas une autre.

18/09/2026. Mesure du jour :

    backend/Dockerfile   FROM python:3.11-slim
    frontend/Dockerfile  FROM python:3.11-slim
    .github/workflows/ci.yml   python-version: "3.12"

Les images livrent **3.11**. La CI valide sur **3.12**. Elle teste donc une
version que personne n'exécute, et son vert ne dit rien de ce qui tourne
vraiment. C'est le même piège que « déployé ≠ source », en plus discret : rien
ne casse, tout est vert, et la première divergence de comportement entre deux
versions passe la porte sans être vue.

Le geste retenu est d'aligner la CI sur ce qui est livré, pas l'inverse : monter
les images de version est une décision de produit, pas un correctif de test.

Ce crible ne fige aucune version. Il exige seulement qu'elles soient **la même**
— le jour où les images passeront à 3.13, il demandera que la CI suive.
"""
import re
from pathlib import Path

import pytest

DEPOT = Path(__file__).resolve().parent.parent.parent


def _version_image(dockerfile: Path) -> str | None:
    trouve = re.search(r"^FROM\s+python:(\d+\.\d+)", dockerfile.read_text(encoding="utf-8-sig"), re.M)
    return trouve.group(1) if trouve else None


def _versions_ci() -> list[str]:
    ci = (DEPOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8-sig")
    return re.findall(r"""python-version:\s*["']?(\d+\.\d+)""", ci)


def _dockerfiles() -> list[Path]:
    return sorted(DEPOT.glob("*/Dockerfile"))


def test_le_crible_voit_bien_les_deux_cotes():
    """Témoin de contenu : sans lui, un chemin changé rendrait le garde muet."""
    images = _dockerfiles()

    assert len(images) >= 2, [str(f) for f in images]
    assert all(_version_image(f) for f in images), {f.parent.name: _version_image(f) for f in images}
    assert _versions_ci(), "la CI ne déclare aucune version de Python"


def test_l_extracteur_lit_bien_une_version_et_pas_autre_chose():
    """Témoin inverse : un extracteur qui rend toujours None passerait tout."""
    assert re.search(r"^FROM\s+python:(\d+\.\d+)", "FROM python:3.11-slim", re.M).group(1) == "3.11"
    assert re.findall(r"""python-version:\s*["']?(\d+\.\d+)""", '  python-version: "3.12"') == ["3.12"]
    assert not re.search(r"^FROM\s+python:(\d+\.\d+)", "FROM node:20-slim", re.M)


@pytest.mark.parametrize("dockerfile", _dockerfiles(), ids=lambda f: f.parent.name)
def test_la_ci_valide_la_version_que_l_image_livre(dockerfile):
    livree = _version_image(dockerfile)
    testees = set(_versions_ci())

    assert testees == {livree}, (
        f"{dockerfile.parent.name}/Dockerfile livre Python {livree}, la CI valide {sorted(testees)}. "
        "Un vert sur une version que personne n'exécute ne prouve rien sur ce qui tourne"
    )
