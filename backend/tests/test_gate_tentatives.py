# -*- coding: utf-8 -*-
"""Une bonne réponse d'une tentative ABANDONNÉE ne doit pas ouvrir la suivante.

Trouvé le 17/09/2026 en cherchant pourquoi `test_gate` échouait une série sur six,
sans aucun plugin d'ordre aléatoire installé. La cause n'était pas les tests :

    _VERIFIED[id] = "ok"   # et la ligne d'avant refuse d'écraser un "ok"

`_VERIFIED` vit dans le processus et n'est vidé qu'au moment où une épreuve est
comptée par `/entry/complete`. Une épreuve réussie dans un parcours qu'on abandonne
y reste donc pour toujours : si un parcours suivant tire la même épreuve et qu'on
la rate, elle compte quand même comme juste. Le seuil d'entrée — qui est une garde,
pas un score de jeu — s'ouvre alors en partie sur une tentative précédente.

La règle voulue n'est pas supprimée, elle est bornée à UNE tentative : dans un même
parcours, une bonne réponse obtenue après un essai raté reste bonne.
"""
from fastapi.testclient import TestClient

from app import entry
from app.main import app


def _bonne_reponse(step):
    c = entry._BY_ID[step["id"]]
    return c.get("answer") or (c.get("choices") or ["x"])[c.get("correct", 0)]


def _premiere_qcm(steps):
    for s in steps:
        c = entry._BY_ID[s["id"]]
        if c.get("choices"):
            return s
    raise AssertionError("le tirage doit contenir au moins un QCM")


def test_une_reussite_d_une_tentative_abandonnee_ne_compte_pas_dans_la_suivante():
    c = TestClient(app)

    # Tentative 1 : on répond juste à une épreuve, puis on abandonne (pas de /entry/complete).
    steps = c.get("/entry/parcours").json()["steps"]
    epreuve = _premiere_qcm(steps)
    r = c.post("/entry/verify", json={"challenge_id": epreuve["id"],
                                      "answer": _bonne_reponse(epreuve)}).json()
    assert r["ok"] is True

    # Tentative 2 : nouveau parcours, la MÊME épreuve, et cette fois une mauvaise réponse.
    c.get("/entry/parcours")
    r2 = c.post("/entry/verify", json={"challenge_id": epreuve["id"],
                                       "answer": "réponse manifestement fausse zzz"}).json()

    final = c.post("/entry/complete", json={"results": [
        {"id": epreuve["id"], "dimension": epreuve["dimension"], "ok": True,
         "answer": "réponse manifestement fausse zzz"}
    ]}).json()

    assert final["score"] == 0, (
        "une réussite d'une tentative abandonnée a été recomptée : "
        f"verify a rendu {r2}, complete a rendu {final}")


def test_dans_une_meme_tentative_une_bonne_reponse_apres_un_rate_reste_bonne():
    """La garantie qu'on ne casse pas : le front autorise les nouvelles tentatives
    avec indice, et une épreuve reprise puis réussie doit rester acquise."""
    c = TestClient(app)
    steps = c.get("/entry/parcours").json()["steps"]
    epreuve = _premiere_qcm(steps)

    c.post("/entry/verify", json={"challenge_id": epreuve["id"], "answer": "zzz faux"})
    c.post("/entry/verify", json={"challenge_id": epreuve["id"],
                                  "answer": _bonne_reponse(epreuve)})

    final = c.post("/entry/complete", json={"results": [
        {"id": epreuve["id"], "dimension": epreuve["dimension"], "ok": True,
         "answer": _bonne_reponse(epreuve)}
    ]}).json()

    assert final["score"] == 1
