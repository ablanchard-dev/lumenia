"""23/09/2026 — Le seuil ne se franchit pas en visant toujours la même lettre.

Mesuré sur la banque : pour les QCM, la bonne réponse est en A dans 74 items sur 168
(44 %, là où un tirage équilibré donnerait 25 %), et les choix étaient servis dans l'ordre
de la banque. Répondre « A » partout battait donc nettement le hasard, sur une garde dont
le rôle est justement de ne pas se contourner.

Désormais : l'ordre des choix est mélangé à CHAQUE tirage, les lettres affichées sont
réattribuées, et la vérification porte sur le TEXTE choisi. Une lettre seule n'est plus
une réponse (sinon « A » partout garderait son avantage côté API).
"""
import random
from collections import Counter

from app.entry import get_parcours, verify_challenge, _BY_ID


def _qcm_items():
    return [c for c in _BY_ID.values() if c["kind"] == "qcm"]


def test_la_banque_est_bien_desequilibree_sinon_ce_test_ne_prouve_rien():
    # Témoin : c'est ce déséquilibre que le mélange doit neutraliser.
    positions = Counter(c["answer"].upper() for c in _qcm_items())
    assert positions["A"] / sum(positions.values()) > 0.35


def test_la_bonne_reponse_n_a_plus_de_position_privilegiee():
    random.seed(20260923)
    positions = Counter()
    for _ in range(300):
        for step in get_parcours()["steps"]:
            if step["kind"] != "qcm":
                continue
            item = _BY_ID[step["id"]]
            juste = item["choices"][item["answer"]]
            lettre = next(L for L, t in step["choices"].items() if t == juste)
            positions[lettre] += 1
    total = sum(positions.values())
    assert total > 1000, "le crible doit avoir vu assez de QCM"
    parts = {L: positions[L] / total for L in "ABCD"}
    hors = {L: f"{p:.1%}" for L, p in parts.items() if not 0.20 < p < 0.30}
    assert hors == {}, f"positions hors de ~25 % : {hors}"


def test_les_lettres_servies_restent_A_B_C_D():
    random.seed(7)
    qcm = [s for s in get_parcours()["steps"] if s["kind"] == "qcm"]
    assert len(qcm) >= 3, "témoin : le tirage doit contenir des QCM"
    for step in qcm:
        assert sorted(step["choices"]) == sorted("ABCD"[: len(step["choices"])])


def test_le_texte_juste_est_accepte_et_la_lettre_seule_refusee():
    item = _qcm_items()[0]
    juste = item["choices"][item["answer"]]
    assert verify_challenge(item["id"], juste).get("ok") is True
    assert verify_challenge(item["id"], item["answer"]).get("ok") is False, (
        "une lettre seule ne peut plus valider : l'ordre servi n'est plus celui de la banque"
    )
