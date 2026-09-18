"""Tests never touch the configured database.

Before: app.db read DATABASE_URL at import, so pytest wrote into whatever database the
machine was configured with, and the fixtures reset `risk.flag` to 0 and set
`entry.passed` to 1 in it. Set before any `app` import (conftest loads first).
"""
import os
import tempfile

_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="lumenia-tests-"), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")


# --- L'etat vivant du processus ne doit pas fuir d'un test a l'autre ----------
#
# 17/09/2026 : deux fuites trouvees le meme jour, par le meme symptome (un test
# qui passe seul et tombe en serie).
#   * `limite._vues` : le compteur d'appels au modele est global au processus.
#     Un fichier de tests qui envoie 20 requetes fermait la porte au fichier
#     suivant, qui recevait 429 au lieu de la reponse attendue.
#   * `main._VERIFIED` : ce que le serveur a constate au parcours d'entree.
#     La cause produit est corrigee (tirer un parcours efface), mais un test qui
#     n'appelle pas `/entry/parcours` heriterait encore de la tentative d'avant.
#
# Remettre a zero AVANT chaque test, c'est isoler ; ce n'est pas assouplir : les
# deux mecanismes gardent exactement le meme comportement dans le produit.
import pytest


@pytest.fixture(autouse=True)
def _etat_de_processus_vierge():
    from app import limite
    from app.main import _VERIFIED

    limite.reset()
    _VERIFIED.clear()
    yield
    limite.reset()
    _VERIFIED.clear()


# --- La reponse bidon des tests du parcours ----------------------------------
#
# 18/09/2026. Elle etait ecrite a la main dans `test_gate.py` : « zzz-non-juge ». Or
# `_matches` compare par SOUS-CHAINE, et six items `objective` de la banque acceptent
# « non ». Pour ces six-la, l'epreuve etait validee sans juge, l'invariant teste ne se
# produisait pas, et le fichier tombait environ 1 fois sur 35.
#
# Elle vit donc a UN seul endroit, et `test_la_reponse_bidon_d_un_test_ne_doit_etre_bonne
# _nulle_part.py` verifie contre la banque qu'elle n'est bonne pour aucun item -- y compris
# apres l'ajout d'un item demain.
REPONSE_BIDON = "qwxzv-kjhgf-mnbvc"
