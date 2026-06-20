"""Tests de la banque d'entrée et du moteur de parcours (app.entry).

Couvre : longueur du parcours (30 questions notées, 6 par dimension), unicité des
ids, validité structurelle des QCM (4 choix distincts, clé valide), présence de
réponses pour les items objectifs, et déterminisme de la validation QCM (lettre
correcte -> ok, lettre incorrecte -> échec) SANS toucher au LLM.
"""
import json
from collections import Counter
from pathlib import Path

import pytest

from app.entry import PARCOURS, get_parcours, verify_challenge

BANK = json.loads(
    (Path(__file__).resolve().parents[1] / "app" / "entry_bank.json").read_text(encoding="utf-8")
)
ALL_ITEMS = [it for dim in BANK for it in dim["pool"]]
QCM = [it for it in ALL_ITEMS if it["kind"] == "qcm"]
OBJECTIVE = [it for it in ALL_ITEMS if it["kind"] == "objective"]
SCORED_DIMS = ("verbale", "fluide", "memoire", "spatial", "vitesse")


# --- Longueur et répartition du parcours -------------------------------------

def test_parcours_draws_30_scored_questions():
    p = get_parcours()
    assert p["total"] == 30
    counts = Counter(s["dimension"] for s in p["steps"])
    for d in SCORED_DIMS:
        assert counts[d] == 6, f"{d} devrait tirer 6 épreuves, a tiré {counts[d]}"
    assert counts.get("libre", 0) == 0  # open = non noté, hors du gate éliminatoire


def test_parcours_steps_carry_qcm_choices():
    p = get_parcours()
    for s in p["steps"]:
        if s["kind"] == "qcm":
            assert s.get("choices"), f"{s['id']} : QCM sans choix dans le parcours"
            assert set(s["choices"]) == set("ABCD"), s["id"]


def test_each_scored_dim_pool_big_enough_to_draw_6():
    by_dim = {dim["dimension"]: dim["pool"] for dim in BANK}
    for d in SCORED_DIMS:
        assert len(by_dim[d]) >= 6, f"{d} : pool trop petit pour tirer 6"


# --- Intégrité structurelle de la banque -------------------------------------

def test_no_duplicate_ids():
    ids = [it["id"] for it in ALL_ITEMS]
    dups = sorted({i for i, n in Counter(ids).items() if n > 1})
    assert dups == [], f"ids dupliqués : {dups}"


def test_every_item_has_question_and_known_kind():
    for it in ALL_ITEMS:
        assert it.get("question", "").strip(), f"{it['id']} : question vide"
        assert it["kind"] in ("qcm", "objective", "open"), f"{it['id']} : kind inconnu"


def test_qcm_structure_valid():
    for it in QCM:
        choices = it.get("choices") or {}
        texts = [str(choices.get(L, "")).strip() for L in "ABCD"]
        assert all(texts), f"{it['id']} : un choix est vide"
        assert len(set(texts)) == 4, f"{it['id']} : choix dupliqués"
        key = str(it.get("answer", "")).upper()
        assert key in set("ABCD"), f"{it['id']} : clé '{key}' invalide"
        assert str(choices.get(key, "")).strip(), f"{it['id']} : la clé pointe un choix vide"


def test_objective_items_have_answers():
    for it in OBJECTIVE:
        assert it.get("answers"), f"{it['id']} : item objectif sans réponses"


# --- Validation déterministe (sans LLM) --------------------------------------

def test_verify_qcm_correct_letter_is_ok():
    for it in QCM:
        assert verify_challenge(it["id"], it["answer"]).get("ok") is True, it["id"]


def test_verify_qcm_wrong_letter_is_rejected():
    for it in QCM:
        wrong = next(L for L in "ABCD" if L != str(it["answer"]).upper())
        assert verify_challenge(it["id"], wrong).get("ok") is False, it["id"]


def test_verify_objective_exact_answer_is_ok(monkeypatch):
    # Passer une réponse acceptée déclenche _matches et DOIT court-circuiter avant
    # le LLM. On fait planter _chat : si un item exact tombe quand même dans la
    # branche LLM (réseau), le test échoue bruyamment au lieu d'appeler le réseau.
    import app.entry as entry_mod

    def _boom(*a, **k):
        raise AssertionError("verify_challenge a appelé le LLM pour une réponse exacte")

    monkeypatch.setattr(entry_mod, "_chat", _boom)
    for it in OBJECTIVE:
        first = str(it["answers"][0])
        assert verify_challenge(it["id"], first).get("ok") is True, it["id"]


def test_verify_unknown_challenge_id():
    assert verify_challenge("__inexistant__", "peu importe").get("ok") is False


@pytest.mark.parametrize("dim", SCORED_DIMS)
def test_dimension_present_in_bank(dim):
    assert any(d["dimension"] == dim for d in BANK)
