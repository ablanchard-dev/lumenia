"""Quand le chat refuse, la personne voit où aller, et le lit sans faute.

23/09/2026 — première vue du chat dans un navigateur qui se croyait « seuil réussi » alors que le
serveur n'avait rien enregistré (vieux navigateur, base remise à zéro, ou la divergence corrigée en
418ec79) : chaque message recevait « Termine-le pour continuer », et depuis le chat AUCUN chemin ne
menait au parcours. Une impasse. Le message lui-même perdait ses accents (« entree valide »,
« detresse », « a tout moment »).
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_le_refus_est_ecrit_en_francais_correct_et_garde_le_3114():
    r = TestClient(app).post("/chat", json={"message": "bonjour", "history": []}).json()
    assert r.get("gated") is True, "témoin : c'est bien le chemin du refus"
    for mot in ("entrée", "détresse", "à tout moment", "3114"):
        assert mot in r["reply"], f"« {mot} » manque dans le refus"


def test_le_navigateur_oublie_son_reussi_perime_et_montre_le_parcours():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    debut = js.index('api("/chat"')
    suite = js[debut:debut + 1500]
    assert re.search(r"\.gated\b", suite), "la réponse « gated » n'est pas lue"
    assert 'removeItem("lumenia.entryPassed")' in suite, "le « réussi » périmé du navigateur survit"
    assert "startParcours" in suite, "aucun chemin du chat vers le parcours"
