# -*- coding: utf-8 -*-
"""Ce que le SERVEUR accepte, pas ce que le front empêche de taper.

Deux familles mesurées le 17/09/2026 :

1. **Les questionnaires cliniques ne vérifiaient ni leur longueur ni leurs valeurs.**
   `phq9_score([0, 0, 0])` rendait `(0, "minimal", False)` : un questionnaire aux
   deux tiers manquants ressortait en « minimal, aucun risque ». Et `[100] * 9`
   rendait 900/« severe ». Le PHQ-9 a **exactement 9 items cotés 0 à 3** (total
   0–27), le GAD-7 en a 7 (total 0–21) : hors de ces bornes, ce n'est pas un score
   bas, c'est **pas un score**. Même famille que le gate d'entrée qui s'ouvrait
   avec un item juste : un résultat incomplet doit être refusé, pas rassurant.

2. **Rien ne bornait les textes envoyés au modèle.** `task`, `thought`, `goal`,
   `context`, `topic`, le journal et l'historique du chat étaient sans limite :
   une seule requête pouvait porter des mégaoctets, facturés à qui héberge.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------- questionnaires cliniques ----------------
@pytest.mark.parametrize("items, pourquoi", [
    ([0, 0, 0], "trois items sur neuf"),
    ([0] * 8, "huit items sur neuf"),
    ([0] * 10, "dix items"),
    ([100] * 9, "valeurs hors échelle"),
    ([-1] * 9, "valeurs négatives"),
    ([4] * 9, "4 n'existe pas sur une échelle 0–3"),
])
def test_un_phq9_qui_n_en_est_pas_un_est_refuse(items, pourquoi):
    r = client.post("/assessment/phq9", json={"items": items})
    assert r.status_code == 422, f"{pourquoi} : accepté avec {r.status_code} → {r.text[:120]}"


def test_un_phq9_complet_et_dans_l_echelle_passe():
    """Le témoin : sans lui, tout refuser ferait passer les six cas précédents."""
    r = client.post("/assessment/phq9", json={"items": [1, 2, 3, 0, 1, 2, 3, 0, 1]})
    assert r.status_code == 200
    assert r.json()["total"] == 13   # le champ s appelle total, verifie sur la vraie reponse


@pytest.mark.parametrize("items", [[0, 0], [0] * 6, [0] * 8, [4] * 7, [-1] * 7])
def test_un_gad7_qui_n_en_est_pas_un_est_refuse(items):
    assert client.post("/assessment/gad7", json={"items": items}).status_code == 422


def test_un_gad7_complet_passe():
    r = client.post("/assessment/gad7", json={"items": [1, 1, 1, 1, 1, 1, 1]})
    assert r.status_code == 200
    assert r.json()["total"] == 7


def test_le_risque_du_neuvieme_item_reste_lu_quand_il_existe():
    """La garantie qu'on ne casse pas en bornant : l'item 9 déclenche le signalement."""
    r = client.post("/assessment/phq9", json={"items": [0] * 8 + [2]})
    assert r.status_code == 200
    assert r.json()["risk_flag"] is True


# ---------------- textes envoyés au modèle ----------------
ENORME = "a" * 20_000

@pytest.mark.parametrize("route, charge", [
    ("/focus/decompose", {"task": ENORME}),
    ("/impostor/reframe", {"thought": ENORME}),
    ("/creativity/generate", {"goal": ENORME}),
    ("/scenarios", {"context": ENORME}),
    ("/psy/coach", {"topic": ENORME}),
    ("/journal", {"title": ENORME, "content": "x"}),
    ("/journal", {"title": "t", "content": ENORME}),
])
def test_un_texte_demesure_est_refuse_avant_d_atteindre_le_modele(route, charge):
    assert client.post(route, json=charge).status_code == 422, route


def test_un_historique_de_chat_ne_peut_pas_etre_infini():
    """Seuls les derniers tours atteignent le modèle, mais le corps entier est
    d'abord lu et analysé : la borne doit être au bord, pas après."""
    historique = [{"role": "user", "content": "bonjour"} for _ in range(500)]
    r = client.post("/chat", json={"message": "salut", "history": historique})
    assert r.status_code == 422


def test_un_usage_normal_n_est_pas_gene():
    r = client.post("/focus/decompose", json={"task": "ranger mon bureau", "steps": 4})
    assert r.status_code == 200
