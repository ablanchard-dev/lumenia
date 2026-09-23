"""Le verdict du seuil vient du serveur, et « pas corrigé » ne se dit jamais « échoué ».

23/09/2026 — deux trous qui se répondaient :

1. Le serveur garde ses constats en mémoire (choix documenté). Depuis la pause du parcours
   (192f787), une personne peut revenir APRÈS un redémarrage : le serveur n'a plus RIEN constaté
   pour elle, et ses épreuves réussies comptaient « ko » → échec au seuil sans une seule faute.
2. Le navigateur recalculait lui-même la réussite et ignorait la réponse de `/entry/complete` :
   le drapeau `undetermined` (18/09, « ne jamais annoncer un échec cognitif pour une panne ») ne
   parvenait jamais à l'écran, et un « réussi » côté navigateur ouvrait le chat pendant que le
   serveur, lui, gardait le seuil fermé.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_sans_aucun_constat_du_serveur_le_parcours_est_non_corrige_pas_echoue():
    c = TestClient(app)
    steps = c.get("/entry/parcours").json()["steps"]
    rendus = [{"id": s["id"], "dimension": s["dimension"], "ok": True, "answer": ""} for s in steps]
    r = c.post("/entry/complete", json={"results": rendus}).json()
    assert r["passed"] is False, "la garde reste fermée"
    assert r["undetermined"] is True, "le serveur n'a rien constaté : il ne peut pas prononcer d'échec"


def test_l_ecran_suit_le_verdict_du_serveur():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    debut = js.index("async function completeParcours")
    corps = js[debut:js.index("\n  }\n", debut)]
    assert re.search(r"\.passed\b", corps), "la réussite affichée ne vient pas du serveur"
    assert re.search(r"\.undetermined\b", corps), "« non corrigé » n'atteint pas l'écran"
    assert "ENTRY_PASS_RATIO" not in corps, "le navigateur recalcule encore le seuil lui-même"
