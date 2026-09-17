# -*- coding: utf-8 -*-
"""Les routes qui appellent un LLM sont les seules a couter de l'argent.

Sans limite, une boucle `while true` sur /chat vide le quota (et le porte-monnaie)
de qui heberge Lumenia. Ce que la limite s'interdit, en revanche : faire taire le
3114. Une reponse 429 porte TOUJOURS le numero, parce qu'une personne en detresse
qui tape trop vite reste une personne en detresse.
"""
import pytest
from fastapi.testclient import TestClient

from app import limite
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _compteurs_vierges():
    limite.reset()
    yield
    limite.reset()


def _envoyer(n, message="bonjour"):
    return [client.post("/chat", json={"message": message, "history": []}) for _ in range(n)]


def test_un_usage_normal_n_est_jamais_freine():
    assert all(r.status_code == 200 for r in _envoyer(limite.PAR_MINUTE))


def test_au_dela_du_quota_la_route_repond_429():
    _envoyer(limite.PAR_MINUTE)
    trop = client.post("/chat", json={"message": "bonjour", "history": []})
    assert trop.status_code == 429
    assert trop.headers["retry-after"].isdigit()


def test_le_429_porte_toujours_le_3114():
    _envoyer(limite.PAR_MINUTE)
    trop = client.post("/chat", json={"message": "bonjour", "history": []})
    assert "3114" in trop.json()["reply"]


def test_la_fenetre_se_rouvre_quand_le_temps_passe():
    _envoyer(limite.PAR_MINUTE)
    assert client.post("/chat", json={"message": "a", "history": []}).status_code == 429
    limite.avancer(61)  # une minute plus tard
    assert client.post("/chat", json={"message": "a", "history": []}).status_code == 200


def test_les_routes_qui_ne_coutent_rien_ne_sont_pas_limitees():
    """Lire une ressource ou l'etat n'appelle aucun LLM : rien a rationner."""
    for _ in range(limite.PAR_MINUTE + 5):
        assert client.get("/resources").status_code == 200
        assert client.get("/healthz").status_code == 200


def test_deux_visiteurs_ne_se_penalisent_pas():
    """Le compteur est par client, pas global : un voisin bruyant ne te ferme pas la porte."""
    for _ in range(limite.PAR_MINUTE):
        client.post("/chat", json={"message": "a", "history": []},
                    headers={"x-forwarded-for": "10.0.0.1"})
    autre = client.post("/chat", json={"message": "a", "history": []},
                        headers={"x-forwarded-for": "10.0.0.2"})
    assert autre.status_code == 200


def test_toutes_les_routes_qui_appellent_un_llm_sont_couvertes():
    """Une route LLM oubliee est une porte ouverte : la liste doit rester complete."""
    attendues = {"/chat", "/focus/decompose", "/impostor/reframe",
                 "/creativity/generate", "/scenarios", "/psy/coach"}
    assert attendues <= limite.ROUTES_LLM
