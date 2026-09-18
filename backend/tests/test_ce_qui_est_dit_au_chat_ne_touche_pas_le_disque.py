# -*- coding: utf-8 -*-
"""La phrase la plus lourde de la page de confidentialité n'était tenue par rien.

`static/confidentialite.html` ouvre la section « Ce qui reste dans votre navigateur » par :

    « Vos conversations sont stockées dans le stockage local de votre navigateur,
      pas sur le serveur. »

C'est LA phrase qui décide si quelqu'un ose écrire ce qu'il a vraiment en tête à une appli
de santé mentale. Le garde existant (`test_la_page_de_confidentialite_reste_exhaustive`)
tient l'inventaire des TABLES : il vérifie que la page nomme exactement celles qui existent.
Il ne dit rien de ce qu'on écrit DEDANS. Ajouter demain un `db.add(Message(...))` dans
`/chat` laisse les quatre tables inchangées, les quatre gardes verts, et la page qui promet
toujours le contraire.

Ce fichier ne lit pas le code : il ENVOIE un message porteur d'une sentinelle et va la
chercher dans toutes les colonnes de toutes les tables. Les trois chemins de `/chat` sont
couverts, y compris la détresse — c'est celui où quelqu'un écrit le plus intime, et c'est
le seul qui écrit déjà en base (le drapeau de risque).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.db import SessionLocal, engine
from app.main import app
from app.models import KV


@pytest.fixture
def client():
    return TestClient(app)


def _ouvrir_le_gate() -> None:
    with SessionLocal() as db:
        kv = db.get(KV, "entry.passed")
        if kv:
            kv.value = "1"
        else:
            db.add(KV(key="entry.passed", value="1"))
        db.commit()


def _tout_ce_que_la_base_contient() -> str:
    """Toutes les lignes de toutes les tables, en un seul texte a fouiller."""
    morceaux = []
    with engine.connect() as cx:
        for table in inspect(engine).get_table_names():
            for ligne in cx.execute(text(f'SELECT * FROM "{table}"')):
                morceaux.append(repr(tuple(ligne)))
    return "\n".join(morceaux)


def _sentinelle() -> str:
    return "sentinelle-" + uuid.uuid4().hex


def test_le_crible_trouve_bien_ce_qui_EST_ecrit(client):
    """Témoin de contenu : sans lui, les tests du dessous seraient verts sur une fouille aveugle.

    Le journal, lui, est écrit en base — la personne l'a demandé en appuyant sur « enregistrer ».
    """
    marqueur = _sentinelle()
    r = client.post("/journal", json={"title": marqueur, "content": "corps"})

    assert r.status_code < 400, r.text
    assert marqueur in _tout_ce_que_la_base_contient(), (
        "le crible ne voit pas une écriture volontaire : il ne prouverait rien sur les autres"
    )


def test_un_message_de_chat_ne_se_retrouve_nulle_part_en_base(client):
    _ouvrir_le_gate()
    marqueur = _sentinelle()

    r = client.post("/chat", json={"message": f"aide moi a organiser ma journee {marqueur}",
                                   "history": []})

    assert r.status_code == 200
    assert not r.json().get("gated")
    assert marqueur not in _tout_ce_que_la_base_contient(), (
        "la page de confidentialité promet que les conversations ne sont PAS sur le serveur"
    )


def test_un_message_de_DETRESSE_ne_se_retrouve_pas_davantage(client):
    """Le chemin qui écrit déjà en base : il pose le drapeau de risque, pas le message.

    C'est le pire endroit où relâcher la promesse : ce que quelqu'un écrit dans cet
    état-là est exactement ce qu'il ne veut pas voir persister sur une machine.
    """
    _ouvrir_le_gate()
    marqueur = _sentinelle()

    r = client.post("/chat", json={"message": f"je veux mourir {marqueur}", "history": []})

    assert r.json().get("risk_flag") is True, "témoin : le chemin de crise doit bien être pris"
    contenu = _tout_ce_que_la_base_contient()
    assert "risk" in contenu, "témoin inverse : ce chemin écrit bien QUELQUE CHOSE en base"
    assert marqueur not in contenu, (
        "le drapeau de risque peut persister ; le texte de la personne, non"
    )


def test_un_message_refuse_par_le_gate_ne_laisse_rien_non_plus(client):
    """Le chemin le plus facile à oublier : la réponse est un refus, pas une conversation."""
    with SessionLocal() as db:
        kv = db.get(KV, "entry.passed")
        if kv:
            kv.value = "0"
            db.commit()

    marqueur = _sentinelle()
    r = client.post("/chat", json={"message": f"aide moi {marqueur}", "history": []})

    assert r.json().get("gated") is True, "témoin : c'est bien le chemin du refus"
    assert marqueur not in _tout_ce_que_la_base_contient()


def test_l_historique_envoye_par_le_client_ne_persiste_pas_non_plus(client):
    """`history` porte toute la conversation précédente : c'est le plus gros volume de texte
    intime qui arrive au serveur à chaque message. Il repart avec la réponse, il ne reste pas."""
    _ouvrir_le_gate()
    marqueur = _sentinelle()

    r = client.post("/chat", json={
        "message": "et ensuite ?",
        "history": [{"role": "user", "content": f"hier je t'ai dit {marqueur}"}],
    })

    assert r.status_code == 200
    assert marqueur not in _tout_ce_que_la_base_contient()
