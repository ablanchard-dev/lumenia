# -*- coding: utf-8 -*-
"""Ce que le champ laisse taper doit être ce que le serveur accepte.

18/09/2026. Deux champs de Lumenia annoncent une limite au visiteur :
`chat-input` (4000) et `challenge-input` (600). Le serveur borne de son côté —
il le doit, un `maxlength` n'est pas une validation, il se contourne d'un clic
dans la console. Mesure du jour : les deux bornes coïncident exactement.

Mais rien ne les tenait ensemble, et les deux dérives font mal, chacune à sa
façon :

- serveur **plus large** que le champ : la borne affichée devient décorative,
  et c'est l'API qui prend ce que le front croyait filtrer ;
- serveur **plus étroit** que le champ : la personne écrit trois mille
  caractères, appuie sur envoyer, et reçoit une erreur. Sur une application
  qu'on ouvre parfois en allant mal, perdre ce qu'on vient d'écrire n'est pas
  un détail d'ergonomie.

Le test exerce donc la vraie route à la longueur exacte, puis à un caractère de
plus.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app import limite
from app.main import app

client = TestClient(app)

# Chaque champ, avec la route qu'il alimente et le nom du champ envoyé.
# Le lien est déclaré ici, à la main : deviner quelle route sert quel champ
# serait de la magie, et une magie qui se trompe est pire que rien.
CHAMPS = [
    ("chat-input", "/chat", lambda texte: {"message": texte, "history": []}),
    ("challenge-input", "/entry/verify", lambda texte: {"challenge_id": "x", "answer": texte}),
]


@pytest.fixture(autouse=True)
def _compteurs_vierges():
    """Ces envois passent par les routes limitées : on ne veut pas mesurer l'anti-spam."""
    limite.reinitialiser()
    yield
    limite.reinitialiser()


def _maxlength(identifiant: str) -> int:
    html = client.get("/").text
    balise = re.search(rf'<(?:input|textarea)[^>]*id="{identifiant}"[^>]*>', html)
    assert balise, f"le champ {identifiant} a disparu de la page"
    limite_affichee = re.search(r'maxlength="(\d+)"', balise.group(0))
    assert limite_affichee, f"le champ {identifiant} n'annonce plus de limite au visiteur"
    return int(limite_affichee.group(1))


@pytest.mark.parametrize("identifiant, route, corps", CHAMPS)
def test_le_serveur_accepte_exactement_ce_que_le_champ_laisse_taper(identifiant, route, corps):
    taille = _maxlength(identifiant)

    reponse = client.post(route, json=corps("a" * taille))

    assert reponse.status_code != 422, (
        f"{identifiant} laisse taper {taille} caractères, et {route} les refuse : "
        "la personne perdrait ce qu'elle vient d'écrire"
    )


@pytest.mark.parametrize("identifiant, route, corps", CHAMPS)
def test_le_serveur_refuse_un_caractere_de_plus(identifiant, route, corps):
    taille = _maxlength(identifiant)

    reponse = client.post(route, json=corps("a" * (taille + 1)))

    assert reponse.status_code == 422, (
        f"{route} accepte plus que les {taille} caractères annoncés : la borne du champ "
        "est décorative, et c'est l'API qui reçoit ce que le front croyait filtrer"
    )


def test_les_deux_champs_sont_bien_ceux_de_la_page():
    """Témoin : si un champ était renommé, les tests ci-dessus ne mesureraient plus
    rien — et sans ce garde, leur silence passerait pour un succès."""
    html = client.get("/").text

    for identifiant, _, _ in CHAMPS:
        assert f'id="{identifiant}"' in html

    tous = re.findall(r'<(?:input|textarea|select)[^>]*maxlength="\d+"[^>]*id="([^"]+)"', html)
    tous += re.findall(r'<(?:input|textarea|select)[^>]*id="([^"]+)"[^>]*maxlength="\d+"', html)
    assert set(tous) == {identifiant for identifiant, _, _ in CHAMPS}, (
        f"un champ annonce une limite sans être mesuré ici : {sorted(set(tous))}"
    )
