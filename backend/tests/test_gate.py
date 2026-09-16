"""Gate serveur : l'accompagnement (/chat) n'est ouvert qu'apres validation du parcours
d'entree (seuil ENTRY_PASS_RATIO), enforce cote SERVEUR et pas seulement au front. La
ressource de crise (3114) reste toujours visible, meme quand le chat est bloque.

16/09 : le serveur comptait le `ok` ENVOYE PAR LE CLIENT. 30 resultats inventes
(`fake0`..`fake29`, tous ok) ouvraient le chat sans repondre a une seule question,
verifie en l'executant. Les anciens tests encodaient cette confiance (ids "0".."29",
ok choisi par le test). Ils jouent maintenant le vrai parcours : tirage, /entry/verify,
puis /entry/complete ; le score vient de ce que le serveur a lui-meme verifie."""
import pytest
from fastapi.testclient import TestClient

from app import entry
from app.entry import entry_passed, ENTRY_PASS_RATIO, _BY_ID
from app.main import app


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    # Juge LLM deterministe : une reponse non reconnue est fausse (pas de reseau en test).
    monkeypatch.setattr(entry, "_chat", lambda *a, **k: "NON")
    # Chaque test part sans epreuve deja verifiee : un "ok" laisse par un autre test
    # masquerait une panne de juge simulee sur la meme epreuve (1 echec vu sur 33 runs).
    from app import main
    main._VERIFIED.clear()


def test_entry_passed_threshold():
    assert ENTRY_PASS_RATIO == 0.85
    assert entry_passed(26, 30) is True          # 0.867 >= 0.85
    assert entry_passed(25, 30) is False         # 0.833 < 0.85
    assert entry_passed(30, 30) is True
    assert entry_passed(0, 30) is False
    assert entry_passed(0, 0) is False           # pas de division par zero


def _good(step):
    item = _BY_ID[step["id"]]
    return item["answer"] if item["kind"] == "qcm" else item["answers"][0]


def _bad(step):
    item = _BY_ID[step["id"]]
    if item["kind"] == "qcm":
        return next(k for k in item["choices"] if k != str(item["answer"]).upper())
    return "zzz-reponse-fausse"


def _play(c, nok, undet_idx=(), monkeypatch=None):
    """Joue un vrai parcours : les `nok` premieres epreuves justes, le reste faux.
    Le client envoie ok=True PARTOUT : le serveur doit l'ignorer."""
    steps = c.get("/entry/parcours").json()["steps"]
    results = []
    for i, step in enumerate(steps):
        if i in undet_idx:
            monkeypatch.setattr(entry, "_chat", lambda *a, **k: None)
            c.post("/entry/verify", json={"challenge_id": step["id"], "answer": "zzz-non-juge"})
            monkeypatch.setattr(entry, "_chat", lambda *a, **k: "NON")
            answer = "zzz-non-juge"
        else:
            answer = _good(step) if i < nok else _bad(step)
            c.post("/entry/verify", json={"challenge_id": step["id"], "answer": answer})
        results.append({"id": step["id"], "dimension": step["dimension"], "ok": True,
                        "skipped": False, "answer": answer})
    return c.post("/entry/complete", json={"results": results}).json(), steps


def _objective_idx(steps, n):
    return tuple(i for i, s in enumerate(steps) if _BY_ID[s["id"]]["kind"] != "qcm")[:n]


def test_chat_is_gated_server_side_until_entry_passed():
    c = TestClient(app)
    # Echec du parcours -> /chat bloque, mais le 3114 reste visible (securite).
    comp, _ = _play(c, 10)
    assert comp["passed"] is False
    g = c.post("/chat", json={"message": "aide moi", "history": []}).json()
    assert g.get("gated") is True
    assert "3114" in g.get("reply", "")

    # Reussite (28/30 = 93%) -> le gate s'ouvre.
    comp, _ = _play(c, 28)
    assert comp["passed"] is True
    ok = c.post("/chat", json={"message": "aide moi a organiser ma journee", "history": []}).json()
    assert not ok.get("gated")
    assert ok.get("reply")

    # Nouvel echec -> re-bloque (l'etat serveur suit le dernier parcours).
    _play(c, 20)
    g2 = c.post("/chat", json={"message": "aide", "history": []}).json()
    assert g2.get("gated") is True


def test_crisis_bypasses_gate():
    # SECURITE : une detresse aigue prime sur le gate.
    c = TestClient(app)
    _play(c, 5)
    r = c.post("/chat", json={"message": "je veux mourir", "history": []}).json()
    assert r.get("gated") is not True
    assert r.get("risk_flag") is True
    assert "3114" in r.get("reply", "")


# --- Le score ne doit pas venir du client ------------------------------------

def test_des_resultats_inventes_n_ouvrent_pas_le_chat():
    c = TestClient(app)
    _play(c, 5)  # etat bloque
    forged = [{"id": f"fake{i}", "dimension": "x", "ok": True, "answer": ""} for i in range(30)]
    r = c.post("/entry/complete", json={"results": forged}).json()
    assert r["passed"] is False
    assert c.post("/chat", json={"message": "salut", "history": []}).json().get("gated") is True


def test_de_vrais_ids_jamais_verifies_ne_comptent_pas():
    c = TestClient(app)
    steps = c.get("/entry/parcours").json()["steps"]
    forged = [{"id": s["id"], "dimension": s["dimension"], "ok": True, "answer": ""} for s in steps]
    r = c.post("/entry/complete", json={"results": forged}).json()
    assert r["passed"] is False
    assert r["score"] == 0


def test_une_bonne_reponse_repetee_ne_compte_qu_une_fois():
    c = TestClient(app)
    step = c.get("/entry/parcours").json()["steps"][0]
    c.post("/entry/verify", json={"challenge_id": step["id"], "answer": _good(step)})
    dup = [{"id": step["id"], "dimension": step["dimension"], "ok": True, "answer": ""}] * 30
    r = c.post("/entry/complete", json={"results": dup}).json()
    assert r["passed"] is False


def test_un_seul_item_juste_ne_passe_plus_a_100_pourcent():
    # Le denominateur reste la longueur du parcours tire, jamais celle envoyee.
    c = TestClient(app)
    step = c.get("/entry/parcours").json()["steps"][0]
    c.post("/entry/verify", json={"challenge_id": step["id"], "answer": _good(step)})
    r = c.post("/entry/complete",
               json={"results": [{"id": step["id"], "dimension": step["dimension"], "ok": True}]}).json()
    assert r["passed"] is False


# --- Une panne de correcteur n'est pas un verdict sur la personne ------------
# Le drapeau vient maintenant de ce que le SERVEUR a constate a /entry/verify : le
# front ne l'envoyait jamais, la protection ne se declenchait donc pas en vrai.

def test_un_item_non_juge_empeche_le_verdict_meme_si_le_score_suffit(monkeypatch):
    c = TestClient(app)
    steps = c.get("/entry/parcours").json()["steps"]
    undet = _objective_idx(steps, 1)
    assert undet, "le tirage doit contenir une epreuve jugee par le LLM"
    # Joue avec le meme tirage que celui inspecte.
    results = []
    for i, step in enumerate(steps):
        if i in undet:
            monkeypatch.setattr(entry, "_chat", lambda *a, **k: None)
            ans = "zzz-non-juge"
        else:
            monkeypatch.setattr(entry, "_chat", lambda *a, **k: "NON")
            ans = _good(step)
        c.post("/entry/verify", json={"challenge_id": step["id"], "answer": ans})
        results.append({"id": step["id"], "dimension": step["dimension"], "ok": True, "answer": ans})
    r = c.post("/entry/complete", json={"results": results}).json()
    assert r["passed"] is False
    assert r["undetermined"] is True, "le serveur doit dire qu'il n'a pas pu corriger"


def test_un_parcours_entierement_juge_reste_normal():
    c = TestClient(app)
    r, _ = _play(c, 26)
    assert r["passed"] is True
    assert r["undetermined"] is False


def test_un_echec_franc_n_est_pas_deguise_en_panne():
    c = TestClient(app)
    r, _ = _play(c, 20)
    assert r["passed"] is False
    assert r["undetermined"] is False, "un echec reel ne doit pas passer pour une panne"


def test_les_items_non_juges_ne_sortent_PAS_du_denominateur():
    c = TestClient(app)
    r, _ = _play(c, 30)
    assert r["total"] == 30, "le denominateur doit rester la longueur du parcours"
