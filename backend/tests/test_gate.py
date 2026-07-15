"""Gate serveur : l'accompagnement (/chat) n'est ouvert qu'apres validation du parcours
d'entree (seuil ENTRY_PASS_RATIO), enforce cote SERVEUR et pas seulement au front. La
ressource de crise (3114) reste toujours visible, meme quand le chat est bloque."""
from fastapi.testclient import TestClient

from app.entry import entry_passed, ENTRY_PASS_RATIO
from app.main import app


def test_entry_passed_threshold():
    assert ENTRY_PASS_RATIO == 0.85
    assert entry_passed(26, 30) is True          # 0.867 >= 0.85
    assert entry_passed(25, 30) is False         # 0.833 < 0.85
    assert entry_passed(30, 30) is True
    assert entry_passed(0, 30) is False
    assert entry_passed(0, 0) is False           # pas de division par zero


def _results(nok, total=30):
    return [{"id": str(i), "dimension": "logique", "ok": i < nok, "skipped": False, "answer": ""}
            for i in range(total)]


def test_chat_is_gated_server_side_until_entry_passed():
    c = TestClient(app)
    # Echec du parcours -> /chat bloque, mais le 3114 reste visible (securite).
    c.post("/entry/complete", json={"results": _results(10)})
    g = c.post("/chat", json={"message": "aide moi", "history": []}).json()
    assert g.get("gated") is True
    assert "3114" in g.get("reply", "")

    # Reussite (28/30 = 93%) -> le gate s'ouvre, vraie reponse d'accompagnement.
    comp = c.post("/entry/complete", json={"results": _results(28)}).json()
    assert comp["passed"] is True
    ok = c.post("/chat", json={"message": "aide moi a organiser ma journee", "history": []}).json()
    assert not ok.get("gated")
    assert ok.get("reply")

    # Nouvel echec -> re-bloque (l'etat serveur suit le dernier parcours).
    c.post("/entry/complete", json={"results": _results(20)})
    g2 = c.post("/chat", json={"message": "aide", "history": []}).json()
    assert g2.get("gated") is True


def test_crisis_bypasses_gate():
    # SECURITE : une detresse aigue prime sur le gate. En etat NON valide, un message de
    # crise doit recevoir la reponse de crise (3114 + risk_flag), pas le message « finis
    # ton test a 85% ». La crise court-circuite le controle d'acces.
    c = TestClient(app)
    c.post("/entry/complete", json={"results": _results(5)})   # parcours echoue -> gated
    r = c.post("/chat", json={"message": "je veux mourir", "history": []}).json()
    assert r.get("gated") is not True
    assert r.get("risk_flag") is True
    assert "3114" in r.get("reply", "")
