# -*- coding: utf-8 -*-
"""`_matches` décide qui passe le parcours d'entrée — et rien ne la tenait.

19/09/2026. Cette fonction est la règle de notation du parcours. Le parcours est
**éliminatoire** (protocole de Blandine, 26/30) : `_matches` décide, épreuve par épreuve, si
quelqu'un obtient le point ou se fait renvoyer au test. Sa docstring annonce trois régimes,
dont une garantie écrite noir sur blanc :

    « Réponse numérique → égalité exacte sur les nombres extraits (« 133 » ne valide pas
      « 33 ») ; réponse textuelle → inclusion en forme compacte ; réponse purement
      symbolique (ex. chiffrement « #%&@ ») → comparaison en ignorant seulement les
      espaces. »

**MESURE AVANT D'ÉCRIRE CE FICHIER** : le régime numérique retiré de `_matches`, la suite
complète passe — **478 verts**. Trois lignes de moins dans une fonction qui en fait quinze,
et la garantie disparaît sans qu'un seul test bouge. Or c'est la simplification la plus
tentante qui soit : les trois régimes *ressemblent* à une inclusion unique.

Ce qui se passerait alors, côté personne : un candidat qui répond **133** à une épreuve dont
la réponse est **33** obtient le point. Sur un test éliminatoire à quatre erreurs près, une
règle de notation qui accepte une réponse fausse n'est pas un détail de confort.

Ce fichier ne change pas `_matches`. Il tient ses trois promesses, une par une.
"""
from __future__ import annotations

import pytest

from app.entry import _matches


# ── Régime 1 : numérique, égalité exacte ─────────────────────────────────────

@pytest.mark.parametrize("attendu, repondu", [
    ("33", "33"),
    ("33", "la reponse est 33"),
    ("33", "  33  "),
    ("0.5", "0,5"),          # la virgule française vaut le point
    ("0.5", "0.5"),
    ("720", "720"),
])
def test_un_nombre_juste_est_accepte(attendu, repondu):
    assert _matches(attendu, repondu) is True


@pytest.mark.parametrize("attendu, repondu", [
    ("33", "133"),   # la promesse citée dans la docstring, mot pour mot
    ("33", "330"),
    ("33", "3"),
    ("5", "15"),
    ("5", "50"),
    ("7", "47"),
    ("0.5", "5"),
])
def test_un_nombre_FAUX_est_refuse_meme_s_il_contient_le_bon(attendu, repondu):
    """Sans le régime numérique, ces réponses passeraient par inclusion de chaîne.

    C'est exactement ce que la mutation a montré : suite verte, règle disparue.
    """
    assert _matches(attendu, repondu) is False


# ── Régime 2 : textuel, inclusion en forme compacte ──────────────────────────

@pytest.mark.parametrize("attendu, repondu", [
    ("non", "non"),
    ("non", "non, je crois pas"),          # une vraie personne répond comme ça
    ("trois", "peut-etre trois"),
    ("germe", "la graine germe"),
    ("germe", "GERME"),                    # la casse ne décide de rien
    ("chat noir", "un chat-noir"),         # tiret, espace : même forme compacte
])
def test_une_reponse_textuelle_est_reconnue_dans_une_phrase(attendu, repondu):
    """La tolérance est délibérée : on note une compréhension, pas une dictée.

    ⚠️ Elle a un coût, mesuré le 18/09 : une valeur « évidemment fausse » écrite à la main
    dans un test contenait « non » et validait six items sans juge. C'est un choix produit
    assumé, pas un oubli — il se resserre avec Blandine, sur la banque, pas ici.
    """
    assert _matches(attendu, repondu) is True


@pytest.mark.parametrize("attendu, repondu", [
    ("germe", "pousse"),
    ("non", "oui"),
    ("trois", "quatre"),
])
def test_une_reponse_textuelle_sans_rapport_est_refusee(attendu, repondu):
    assert _matches(attendu, repondu) is False


# ── Régime 3 : symbolique, on n'ignore que les espaces ───────────────────────

@pytest.mark.parametrize("attendu, repondu", [
    ("#%&@", "#%&@"),
    ("#%&@", "# % & @"),
    ("<-->", "la fleche <--> ici"),
])
def test_une_reponse_purement_symbolique_reste_comparable(attendu, repondu):
    """La compaction alphanumérique viderait ces réponses : elles deviendraient vraies
    partout. Le troisième régime existe pour ça, et il se prouve."""
    assert _matches(attendu, repondu) is True


def test_une_reponse_symbolique_differente_est_refusee():
    assert _matches("#%&@", "@&%#") is False


# ── Le témoin des trois régimes ──────────────────────────────────────────────

def test_les_trois_regimes_sont_bien_DISTINCTS():
    """Sans lui, un `_matches` réduit à l'inclusion de chaîne passerait la moitié des tests
    ci-dessus et on croirait la règle tenue.

    Chaque ligne est un comportement qu'une inclusion simple ne produit PAS.
    """
    # Une inclusion simple dirait « oui » : le régime numérique dit non.
    assert _matches("33", "133") is False
    # Une inclusion simple sur la forme compacte dirait « non » : le régime textuel dit oui.
    assert _matches("chat noir", "un chat-noir") is True
    # Une compaction alphanumérique viderait la cible : le régime symbolique la garde.
    assert _matches("#%&@", "#%&@") is True
