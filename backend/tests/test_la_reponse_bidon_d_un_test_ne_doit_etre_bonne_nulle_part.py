# -*- coding: utf-8 -*-
"""Le flake de `test_gate`, explique et ferme — 18/09/2026.

Mesure du tour 107 : `test_un_item_non_juge_empeche_le_verdict_meme_si_le_score_suffit`
tombait **1 fois sur 35 environ**. Deux hypotheses ont ete refutees par mesure (un tirage
sans epreuve jugee par le LLM : 0/200 ; un premier non-QCM de kind `open` : 0/300).

La cause, mesuree ici : ce test envoie une reponse volontairement fausse — `"zzz-non-juge"` —
et attend que le juge LLM soit consulte, donc que l'epreuve ressorte NON JUGEE. Mais
`_matches` compare par SOUS-CHAINE sur les symboles normalises, et **six items `objective`
de la banque acceptent « non »**. `"zzz-non-juge"` contient « non » : pour ces six-la,
l'epreuve est validee tout de suite, sans juge, et l'invariant teste ne se produit jamais.

6 items sur 117 `objective`, tires en premiere position non-QCM : ~3 %. C'est exactement le
taux observe.

Ce fichier ne corrige pas `_matches` — la tolerance par sous-chaine est un choix produit,
et le resserrer se decide sur la banque, pas dans un test. Il rend la reponse bidon
**derivee** : elle doit n'etre acceptee par AUCUN item de la banque. Ecrite a la main, elle
redeviendra fausse le jour ou quelqu'un ajoutera un item ; derivee, elle rougit ce jour-la.
"""
from __future__ import annotations

from app.entry import _BY_ID, _matches

# La reponse bidon employee par les tests du parcours. Un seul endroit, et un test la tient.
from conftest import REPONSE_BIDON  # la constante vit a UN seul endroit
# Premier candidat essaye : « qwxzv-reponse-sans-rapport-qwxzv ». Il contenait « reponse »,
# accepte par l'item `cle_question` -- la meme faute que celle qu'on corrige, commise en la
# corrigeant. C'est exactement pour ca que ce fichier existe : seules des suites de consonnes
# sans mot francais tiennent, et seule une VERIFICATION contre la banque le prouve.


def _objectives() -> list[dict]:
    return [i for i in _BY_ID.values() if i["kind"] == "objective"]


def _acceptee_par(reponse: str) -> list[tuple[str, str]]:
    trouves = []
    for item in _objectives():
        for accepte in item.get("answers", []):
            if _matches(accepte, reponse):
                trouves.append((item["id"], accepte))
                break
    return trouves


def test_le_crible_voit_bien_la_banque():
    """Témoin : sans lui, une banque vide rendrait tout vert sans rien regarder."""
    assert len(_objectives()) > 50, "le crible doit avoir de vrais items à examiner"


def test_l_ANCIENNE_reponse_bidon_etait_bonne_pour_six_items():
    """La cause du flake, gardée comme fait mesuré et non comme souvenir.

    Si un jour ce test devient faux, c'est que la banque a changé — et la leçon reste :
    une réponse bidon écrite à la main est bonne quelque part tôt ou tard.
    """
    acceptee = _acceptee_par("zzz-non-juge")

    assert acceptee, (
        "la réponse bidon historique n'est plus acceptée nulle part : le flake de "
        "`test_gate` ne venait donc plus de là, et ce fichier doit être relu"
    )
    assert all(a.strip().lower() == "non" for _, a in acceptee), (
        "toutes ces acceptations passent par « non », contenu dans « zzz-non-juge » : "
        f"{acceptee}"
    )


def test_la_reponse_bidon_employee_n_est_bonne_pour_AUCUN_item():
    """L'invariant qui ferme le flake, et qui rougira si la banque évolue."""
    acceptee = _acceptee_par(REPONSE_BIDON)

    assert acceptee == [], (
        "cette réponse est censée n'être bonne nulle part : sans ça, l'épreuve est validée "
        "sans juge et le test qui attend une épreuve NON JUGÉE tombe au hasard des tirages. "
        f"Acceptée par : {acceptee}"
    )


def test_la_reponse_bidon_reste_une_vraie_reponse_et_pas_du_vide():
    """Le contrepoids : une chaîne vide ne serait acceptée nulle part non plus, et ne
    prouverait rien — `verify_challenge` la refuserait avant même de juger."""
    assert len(REPONSE_BIDON.strip()) >= 2
    assert any(c.isalpha() for c in REPONSE_BIDON)
