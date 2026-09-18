# -*- coding: utf-8 -*-
"""Refuser une saisie, sans la répéter.

18/09/2026. Les bornes de taille sont posées depuis le 17/09 : un message de
5 000 caractères est refusé, une entrée de journal de 20 000 aussi. Mesure du
jour sur ce que le refus **répond** :

    POST /chat {"message": "a"*5000}
    422 {"detail":[{"type":"string_too_long","loc":["body","message"],
                    "msg":"...","input":"aaaa…"}]}

Le champ `input` de Pydantic contient **le texte entier que la personne vient
d'écrire**. Sur Lumenia, ce texte, c'est ce qu'elle dit d'elle : une pensée
intrusive, une nuit difficile, un passage à vide. Il repart alors dans un corps
d'erreur — la seule catégorie de réponse que les proxys, les journaux d'accès et
les rapports de plantage côté navigateur conservent volontiers, précisément
parce que c'est une erreur.

Le front n'y est pour rien : il lit `res.ok` et ne recopie rien. La fuite est
dans la réponse elle-même, et elle est silencieuse — tout marche.

Ce que le refus doit garder : **quel champ**, et **pourquoi**. Sans ça on
remplace une fuite par une panne muette, et personne ne saura corriger sa
saisie.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SECRET = "je n ai pas dormi depuis trois nuits et je ne sais plus quoi faire"

# Une saisie refusée par route, avec le secret DEDANS : c'est lui qu'on suit.
REFUSES = [
    ("/chat", {"message": SECRET + "a" * 5_000}),
    ("/journal", {"title": "titre", "content": SECRET + "a" * 20_000}),
    ("/entry/verify", {"challenge_id": "c1", "answer": SECRET + "a" * 1_000}),
    ("/impostor/reframe", {"thought": SECRET + "a" * 3_000}),
]


@pytest.mark.parametrize("chemin,corps", REFUSES)
def test_le_crible_obtient_bien_un_refus(chemin, corps):
    """Témoin : sans un vrai 422, tout ce qui suit serait vert sur du vide."""
    assert client.post(chemin, json=corps).status_code == 422, (
        f"{chemin} accepte cette saisie : le test suivant ne prouverait rien"
    )


@pytest.mark.parametrize("chemin,corps", REFUSES)
def test_un_refus_ne_repete_pas_ce_que_la_personne_a_ecrit(chemin, corps):
    reponse = client.post(chemin, json=corps)

    assert SECRET not in reponse.text, (
        f"{chemin} renvoie dans son corps d'erreur le texte que la personne vient "
        "d'écrire. Un corps 422 est justement ce qu'un proxy ou un rapport de "
        "plantage conserve : c'est une fuite, et rien ne la signale"
    )


@pytest.mark.parametrize("chemin,corps", REFUSES)
def test_un_refus_dit_toujours_quel_champ_et_pourquoi(chemin, corps):
    """La garde d'en face : taire l'erreur remplacerait la fuite par une panne muette.

    Le champ et la raison suffisent à corriger une saisie ; la valeur ne sert
    qu'à celui qui l'a déjà.
    """
    detail = client.post(chemin, json=corps).json()["detail"]

    assert detail, f"{chemin} refuse sans dire quoi que ce soit"
    for faute in detail:
        assert faute.get("loc"), f"{chemin} ne dit pas quel champ est en cause : {faute}"
        assert faute.get("msg"), f"{chemin} ne dit pas pourquoi : {faute}"


def test_une_erreur_de_forme_ne_renvoie_pas_le_corps_non_plus():
    """L'autre porte : un corps illisible passe par le même gestionnaire.

    Ici Pydantic ne met pas le texte dans `input` mais dans `ctx`, et un corps
    JSON casse est tout aussi capable de porter ce que quelqu'un a ecrit.
    """
    reponse = client.post(
        "/chat",
        content=('{"message": "' + SECRET + '"').encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    assert reponse.status_code == 422
    assert SECRET not in reponse.text, reponse.text[:200]
