# -*- coding: utf-8 -*-
"""Le juge du parcours d'entrée est un appel au modèle que personne ne rationnait.

`app/limite.py` s'ouvre sur : « Limite de debit sur les seules routes qui appellent un
LLM ». Six routes y sont rationnées à 20/min. Une septième surface appelle le modèle et
n'y figure pas : `POST /entry/verify`.

Le chemin : `entry_verify` → `verify_challenge` → `_chat`. Une épreuve `objective` dont la
réponse ne figure pas dans la liste de synonymes part chez le juge — et 117 des items de
la banque sont `objective`. La route tombe donc dans le budget des ÉCRITURES (120/min,
dimensionné sur le disque, pas sur le quota) : **six fois le plafond de conversation, sur
une surface qui coûte exactement la même chose à chaque appel.**

Le garde `test_aucune_route_llm_ne_peut_etre_oubliee` ne le voyait pas : il déduit les
routes LLM en lisant le corps des fonctions de `main.py`, un seul cran de profondeur. Ici
l'appel est deux crans plus bas, dans un autre module. Un crible juste peut regarder à
côté.

Ce que ce fichier fixe : le juge a son propre plafond, GLOBAL au processus — c'est le
quota de qui héberge qui est en jeu, et il est global, lui aussi. Au-delà, l'épreuve
ressort `undetermined` : l'état que le produit sait déjà tenir honnêtement (« juge
injoignable, épreuve NON JUGÉE »), et non un faux « c'est faux ».
"""
from __future__ import annotations

import pytest

from app import entry, limite


APPELS: list[str] = []


@pytest.fixture
def juge_compte(monkeypatch):
    """Un juge qui répond toujours OUI et qui compte ses passages."""
    APPELS.clear()

    def _faux_chat(prompt, **kw):
        APPELS.append(prompt)
        return "OUI"

    monkeypatch.setattr(entry, "_chat", _faux_chat)
    return APPELS


def _une_epreuve_objective() -> str:
    objectives = [i for i in entry._BY_ID.values() if i["kind"] == "objective"]
    assert objectives, "témoin de contenu : la banque doit porter des épreuves jugées"
    return objectives[0]["id"]


def test_le_juge_a_bien_ete_atteint(juge_compte):
    """Témoin : sans lui, le test du dessous serait vert sur un chemin jamais pris."""
    entry.verify_challenge(_une_epreuve_objective(), "une réponse que la liste ignore")
    assert len(juge_compte) == 1


def test_le_juge_ne_part_pas_plus_que_son_plafond(juge_compte):
    """Sans plafond, une boucle sur /entry/verify vide le quota de qui héberge Lumenia."""
    epreuve = _une_epreuve_objective()

    for i in range(limite.PAR_MINUTE_JUGE + 50):
        entry.verify_challenge(epreuve, f"formulation inconnue numero {i}")

    assert len(juge_compte) == limite.PAR_MINUTE_JUGE, (
        "le juge est parti " + str(len(juge_compte)) + " fois : le plafond ne tient pas"
    )


def test_au_dela_du_plafond_l_epreuve_est_NON_JUGEE_et_pas_FAUSSE(juge_compte):
    """La différence engage un candidat : « je ne sais pas » n'est pas « c'est faux ».

    Le produit distingue déjà les deux quand le juge est injoignable. Un plafond qui
    répondrait « faux » ferait échouer un candidat valable parce que quelqu'un d'autre
    a bouclé sur la route une minute plus tôt.
    """
    epreuve = _une_epreuve_objective()

    for i in range(limite.PAR_MINUTE_JUGE):
        entry.verify_challenge(epreuve, f"formulation inconnue numero {i}")

    apres = entry.verify_challenge(epreuve, "encore une formulation inconnue")

    assert apres["ok"] is False
    assert apres.get("undetermined") is True, (
        "une épreuve non jugée doit rester visible comme telle, sinon la panne est "
        "indiscernable d'une vraie erreur du candidat"
    )


def test_le_plafond_du_juge_est_GLOBAL_et_pas_par_visiteur(juge_compte):
    """C'est le porte-monnaie de l'hébergeur qui est en jeu, et il n'a pas d'adresse IP.

    Un plafond par visiteur laisse N visiteurs multiplier la facture par N.
    """
    epreuve = _une_epreuve_objective()
    for i in range(limite.PAR_MINUTE_JUGE):
        entry.verify_challenge(epreuve, f"visiteur A, formulation {i}")

    # Aucune notion de client ici : le compteur ne peut pas être contourné en changeant
    # d'adresse, puisqu'il n'en lit aucune.
    entry.verify_challenge(epreuve, "visiteur B, formulation neuve")

    assert len(juge_compte) == limite.PAR_MINUTE_JUGE
