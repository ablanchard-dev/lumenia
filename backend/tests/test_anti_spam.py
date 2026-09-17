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


def test_toutes_les_routes_qui_appellent_un_llm_sont_couvertes():
    """Une route LLM oubliee est une porte ouverte : la liste doit rester complete."""
    attendues = {"/chat", "/focus/decompose", "/impostor/reframe",
                 "/creativity/generate", "/scenarios", "/psy/coach"}
    assert attendues <= limite.ROUTES_LLM


def test_changer_d_en_tete_ne_donne_pas_un_quota_neuf():
    """🔴 La limite protege le porte-monnaie de qui heberge Lumenia. Si `x-forwarded-for`
    suffit a repartir de zero, elle ne protege rien : une boucle de dix lignes qui
    incremente l'en-tete appelle le LLM sans fin. L'en-tete est ecrit par le client, il
    n'est donc une identite que derriere un proxy qu'on a nous-meme declare.
    """
    assert not limite.derriere_un_proxy(), "par defaut, aucun proxy n'est declare"

    refuses = 0
    for i in range(limite.PAR_MINUTE * 3):
        r = client.post("/chat", json={"message": "a", "history": []},
                        headers={"x-forwarded-for": f"10.0.0.{i}"})
        refuses += r.status_code == 429
    assert refuses > 0, "un en-tete different a chaque appel a contourne la limite"


def test_derriere_un_proxy_declare_l_en_tete_redevient_l_identite(monkeypatch):
    """Et l'inverse : chez un hebergeur qui met un proxy devant (Render, Fly...), tous les
    appels arrivent avec la MEME IP de sortie. Sans lire l'en-tete, un visiteur bruyant
    fermerait la porte a tous les autres. C'est pour ca que le mode existe -- declare.
    """
    monkeypatch.setenv("LUMENIA_DERRIERE_PROXY", "1")
    limite.reset()

    for _ in range(limite.PAR_MINUTE):
        client.post("/chat", json={"message": "a", "history": []},
                    headers={"x-forwarded-for": "10.0.0.1"})
    autre = client.post("/chat", json={"message": "a", "history": []},
                        headers={"x-forwarded-for": "10.0.0.2"})
    assert autre.status_code == 200


def test_le_compteur_ne_garde_pas_tous_les_visiteurs_pour_toujours():
    """🔴 Deuxieme moitie de la meme attaque. Derriere un proxy declare, l'en-tete redevient
    l'identite -- et une boucle qui l'incremente cree alors une entree par valeur, jamais
    relue, jamais liberee : la memoire du serveur monte jusqu'a ce qu'il tombe. Une entree
    dont la fenetre est passee n'apprend plus rien ; elle doit partir.
    """
    combien = limite.VISITEURS_AVANT_BALAYAGE + 100
    for i in range(combien):
        limite.autorise(f"10.1.{i // 256}.{i % 256}")
    limite.avancer(limite.FENETRE + 1)
    limite.autorise("10.2.0.1")

    assert len(limite._vues) < combien, (
        f"{len(limite._vues)} visiteurs perimes sont encore en memoire"
    )
