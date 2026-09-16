"""La detection de crise vaut pour TOUT texte libre, pas seulement /chat.

Revue 17/09, verifie en l'executant : « je veux mourir, aide moi » envoye a /focus/decompose
partait au LLM et revenait en decomposition de tache, sans le 3114. Idem pour reframe,
creativity, scenarios et psy/coach (qui ne regardait que le drapeau deja pose). Ces routes
ignoraient aussi le gate d'entree que /chat applique. Le journal enregistrait une detresse
sans rien declencher.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as m
from app.main import app

MSG = "je veux mourir, aide moi"
ROUTES = [
    ("/focus/decompose", {"task": MSG}, "decompose"),
    ("/impostor/reframe", {"thought": MSG}, "reframe"),
    ("/creativity/generate", {"goal": MSG}, "creative"),
    ("/scenarios", {"context": MSG}, "scenarios"),
    ("/psy/coach", {"topic": MSG}, "psycho_coach"),
]


def _set_kv(key, value):
    with m.SessionLocal() as db:
        kv = db.get(m.KV, key)
        if kv:
            kv.value = value
        else:
            db.add(m.KV(key=key, value=value))
        db.commit()


@pytest.fixture
def llm_calls(monkeypatch):
    calls = []
    for _, _, fn in ROUTES:
        monkeypatch.setattr(m, fn, lambda *a, _fn=fn, **k: calls.append(_fn) or "REPONSE LLM")
    _set_kv("risk.flag", "0")
    _set_kv("entry.passed", "1")
    return calls


@pytest.mark.parametrize("path,body,fn", ROUTES)
def test_detresse_sur_toute_route_llm_donne_le_3114_sans_appeler_le_llm(llm_calls, path, body, fn):
    r = TestClient(app).post(path, json=body).json()
    assert "3114" in str(r), f"{path} : pas de reponse de crise"
    assert fn not in llm_calls, f"{path} : le texte de detresse est parti au LLM"


@pytest.mark.parametrize("path,body,fn", [x for x in ROUTES if x[0] != "/psy/coach"])
def test_routes_llm_fermees_tant_que_le_parcours_n_est_pas_valide(llm_calls, path, body, fn):
    _set_kv("entry.passed", "0")
    neutre = {k: "organiser ma semaine" for k in body}
    r = TestClient(app).post(path, json=neutre).json()
    assert r.get("gated") is True
    assert fn not in llm_calls


def test_journal_enregistre_mais_une_detresse_declenche_la_reponse_de_crise(llm_calls):
    r = TestClient(app).post("/journal", json={"title": "soir", "content": MSG}).json()
    assert r.get("id") is not None, "l'entree doit rester enregistree"
    assert r.get("risk_flag") is True and "3114" in str(r)
