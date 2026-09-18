# -*- coding: utf-8 -*-
"""Le protocole dit « **>=** 85 % ». Rien ne tenait le sens de cette comparaison.

19/09/2026, trouvé par balayage de mutations sur les règles de décision de Lumenia :
`entry_passed` dont le `>=` devient `>` laisse **toute la suite verte**. Quatre autres
mutations du même balayage (gradabilité, plafond du limiteur, longueur du parcours, plafond
du juge) font rougir immédiatement — celle-ci, non.

**Pourquoi le test existant ne la voit pas.** `test_entry_passed_threshold` vérifie 26/30,
25/30, 30/30, 0/30, 0/0. Aucun de ces cas n'est *pile* au seuil : avec 30 épreuves notées,
85 % vaut 25,5 — un score qui n'existe pas. La frontière exacte est **inatteignable avec le
tirage d'aujourd'hui**, donc jamais éprouvée.

**Pourquoi ça compte quand même.** La longueur du parcours est DÉRIVÉE (`entry_scored_length`
lit `_DRAW_PER_DIM`), pas figée. Le jour où une dimension passe à 5 épreuves, ou qu'une
dimension est retirée, la frontière devient atteignable — 17/20 fait exactement 0,85 — et le
sens de la comparaison décide alors du sort de quelqu'un. Un `>` renvoie au test la personne
**pile au seuil**, c'est-à-dire précisément celle que le protocole clinique voulait admettre.

Ces tests fabriquent donc la frontière au lieu de l'attendre du tirage.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from app.entry import ENTRY_PASS_RATIO, entry_passed, entry_scored_length


def _pile_au_seuil() -> list[tuple[int, int]]:
    """Des couples (score, total) qui valent EXACTEMENT le seuil, quel qu'il soit."""
    part = Fraction(ENTRY_PASS_RATIO).limit_denominator(1000)
    return [(part.numerator * k, part.denominator * k) for k in (1, 2, 5)]


def test_le_temoin_de_ce_fichier_la_frontiere_n_est_PAS_atteignable_aujourd_hui():
    """Sans ce témoin, on croirait le cas déjà couvert par les tests du tirage réel.

    Si un jour il rougit, c'est une bonne nouvelle : la frontière sera devenue atteignable
    avec le vrai parcours — et les tests du dessous seront alors la seule chose qui aura
    empêché la règle de basculer en silence.
    """
    total = entry_scored_length()
    scores_possibles = {k / total for k in range(total + 1)}

    assert ENTRY_PASS_RATIO not in scores_possibles, (
        f"avec {total} épreuves notées, un score vaut exactement {ENTRY_PASS_RATIO} : "
        "les tests du tirage réel couvrent désormais la frontière, ce fichier peut être relu"
    )


@pytest.mark.parametrize("score, total", _pile_au_seuil())
def test_qui_est_PILE_au_seuil_est_admis(score, total):
    """« >= 85 % » : le protocole de Blandine admet le seuil, il ne le refuse pas.

    C'est la mutation qui ne cassait rien : `>=` devenu `>` renvoie au test la personne
    exactement au seuil.
    """
    assert entry_passed(score, total) is True, (
        f"{score}/{total} vaut exactement le seuil : le protocole dit « au moins », "
        "pas « strictement plus »"
    )


@pytest.mark.parametrize("score, total", _pile_au_seuil())
def test_une_seule_epreuve_en_dessous_du_seuil_ne_passe_pas(score, total):
    """Le contrepoids : admettre le seuil ne veut pas dire admettre en dessous.

    Sans lui, on satisferait le test du dessus avec un `entry_passed` qui rend toujours True.
    """
    assert entry_passed(score - 1, total) is False


def test_le_seuil_employe_est_bien_celui_du_protocole_et_pas_une_copie():
    """Le chiffre est clinique : il vient de `ENTRY_PASS_RATIO`, jamais réécrit ici.

    Les couples ci-dessus sont dérivés de cette constante — changer le protocole change les
    cas testés, au lieu de rendre ce fichier faux en silence.
    """
    couples = _pile_au_seuil()
    # Temoin de non-vacuite (crible du 18/09) : une liste vide rendrait cette boucle muette
    # et ce test vert sans avoir rien verifie.
    assert len(couples) >= 3, "le crible doit avoir de vrais couples a examiner"

    for score, total in couples:
        assert score / total == pytest.approx(ENTRY_PASS_RATIO, abs=1e-12)
