# -*- coding: utf-8 -*-
"""La limite protégeait le porte-monnaie, pas le disque.

18/09/2026. `limite.py` s'ouvre sur sa propre règle :

    « Limite de debit sur les seules routes qui appellent un LLM. [...]
      Les routes de lecture ne coutent rien et ne sont pas rationnees. »

La phrase décrit deux catégories — les routes qui appellent un modèle, et les
*lectures*. Le code, lui, en laisse passer une troisième : **les écritures**.
`POST /journal`, `POST /assessment/entry`, `POST /assessment/phq9` écrivent en
base, ne coûtent pas un centime de quota, et ne sont rationnées par rien.

Mesure du jour : 40 `POST /journal` d'affilée, 40 fois 200. Chaque entrée peut
porter 10 000 caractères (`TexteLong`) — la borne d'entrée est là et elle est
bonne, mais elle borne *une* requête, pas leur nombre. Personne n'a besoin d'être
malveillant : une boucle qui se répète remplit le disque de qui héberge, et c'est
ce même disque que `/journal/export` rendra ensuite.

Le correctif ne touche pas au budget des routes LLM (20/min, étroit exprès) : il
donne aux écritures leur propre budget, plus large — assez pour quelqu'un qui
écrit vraiment, trop étroit pour une boucle. Et il ne dérive plus d'une liste
écrite à la main : **c'est la méthode HTTP qui décide**, donc une route d'écriture
ajoutée demain naît protégée.
"""
import pytest

from fastapi.testclient import TestClient

from app import limite
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _compteurs_neufs():
    limite.reset()
    yield
    limite.reset()


def test_le_crible_ecrit_bien_dans_le_journal():
    """Témoin : si la route n'écrivait plus, le test suivant serait vert sur du vide."""
    r = client.post("/journal", json={"title": "note", "content": "texte"})

    assert r.status_code == 200, r.text


def test_une_boucle_d_ecriture_finit_par_etre_arretee():
    codes = [
        client.post("/journal", json={"title": f"n{i}", "content": "x" * 100}).status_code
        for i in range(limite.PAR_MINUTE_ECRITURE + 5)
    ]

    assert 429 in codes, (
        f"{len(codes)} ecritures d'affilee, aucune refusee. Une entree peut porter 10 000 "
        "caracteres : la borne d'entree limite UNE requete, pas leur nombre. Une boucle "
        "remplit le disque de qui heberge — et c'est ce disque que /journal/export rend ensuite"
    )


def test_quelqu_un_qui_ecrit_vraiment_n_est_pas_gene():
    """L'autre sens, et il compte plus que le premier sur une appli de santé mentale."""
    codes = [
        client.post("/journal", json={"title": f"n{i}", "content": "ce que j'ai vecu aujourd'hui"}).status_code
        for i in range(20)
    ]

    assert codes == [200] * 20, (
        f"vingt entrees d'affilee doivent passer : {codes}. Quelqu'un qui vide son sac un soir "
        "ne doit jamais rencontrer une porte fermee"
    )


def test_le_budget_des_routes_llm_reste_le_sien():
    """Les deux budgets ne doivent pas se confondre : le modèle coûte, le disque non."""
    assert limite.PAR_MINUTE_ECRITURE > limite.PAR_MINUTE, (
        "ecrire dans son journal doit etre plus large qu'appeler un modele"
    )


def test_une_lecture_n_est_toujours_pas_rationnee():
    codes = [client.get("/resources").status_code for _ in range(limite.PAR_MINUTE_ECRITURE + 5)]

    assert codes == [200] * len(codes), "lire ne coute rien : la regle de la maison n'a pas change"
