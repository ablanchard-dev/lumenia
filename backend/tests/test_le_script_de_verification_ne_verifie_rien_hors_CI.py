# -*- coding: utf-8 -*-
"""Vingt-cinq cas de crise vérifiés par un script que rien n'exécute.

19/09/2026. À la racine du dépôt vit `_verify_crisis.py` : vingt-cinq phrases, chacune
avec son attendu, et il passe 25/25. Il est soigné — il sépare les signaux forts des
tournures innocentes, exactement comme il faut.

Personne ne le lance. Il n'est ni dans la CI, ni dans la suite pytest, ni cité par le
README. Sa couverture n'existe que le jour où quelqu'un tape son nom.

MESURE, fragment par fragment plutôt que phrase entière — pour ne pas confondre une
formulation absente avec une simple différence d'accent :

    "kill myself"      → 6 fichiers de test        couvert
    "me pendre"        → 3                          couvert
    "better off dead"  → 3                          couvert
    "tuer le temps"    → 3                          couvert
    "sui cide"         → 0    ← la forme COMPACTE, la deuxième couche de détection
    "end my life"      → 0
    "foutre en l'air"  → 0    (la variante SANS apostrophe est couverte, pas celle-ci)

Trois cas donc.

🔴 ET J'AI FAILLI EN DIRE PLUS QUE LA MESURE. J'avais écrit ici que `sui cide` était la
**seule** phrase du dépôt à exercer la couche des formes compactes. Mutation faite — la
couche compacte désactivée — le corpus de la CI rougit **lui aussi** : `jveux mourir` la
traverse depuis toujours. La phrase était fausse, et c'est la mutation qui l'a dit, pas
la lecture. Ce qui reste vrai : `sui cide` est la seule qui exerce l'espacement
**volontaire** au milieu du mot, et elle ne vivait que dans le script.

CE QUE CE FICHIER FAIT. Il ne recopie pas : il **lit le script** et exige que chacun de
ses cas soit vérifié ici. Deux listes tenues à la main divergent toujours — celle-ci en
est la preuve, elles ont divergé de trois phrases sur la détection de crise. Une phrase
ajoutée demain au script tombe sous le même test le jour même.

⚠️ Le script n'est pas supprimé : retirer un fichier est une décision d'Alex. Il reste
lançable à la main, et devient la source que la CI relit.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.chat import detect_crisis

SCRIPT = Path(__file__).resolve().parents[2] / "_verify_crisis.py"


def _cas_du_script() -> list[tuple[str, bool]]:
    """(phrase, attendu) lus dans le script — jamais recopiés ici."""
    arbre = ast.parse(SCRIPT.read_text(encoding="utf-8"))

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign):
            continue
        if not any(isinstance(c, ast.Name) and c.id == "TESTS" for c in noeud.targets):
            continue

        cas = []
        for element in noeud.value.elts:  # type: ignore[attr-defined]
            phrase, attendu = element.elts
            cas.append((ast.literal_eval(phrase), ast.literal_eval(attendu)))
        return cas

    raise AssertionError("la table `TESTS` du script est introuvable")


def test_le_crible_lit_bien_le_script():
    """Témoin : sans lui, un script renommé rendrait tout le reste vert sur du vide."""
    cas = _cas_du_script()

    assert len(cas) >= 20, cas
    assert any(attendu for _, attendu in cas), "des cas de détresse doivent exister"
    assert any(not attendu for _, attendu in cas), "et des cas neutres aussi"


@pytest.mark.parametrize("phrase,attendu", _cas_du_script())
def test_chaque_cas_du_script_est_verifie_en_CI(phrase, attendu):
    assert detect_crisis(phrase) is attendu, phrase


def test_la_forme_COMPACTE_est_exercee_par_au_moins_une_phrase():
    """L'espacement volontaire au milieu du mot, qui n'existait que dans le script.

    `detect_crisis` a deux couches : les motifs, et les formes compactes. La seconde est
    déjà exercée par `jveux mourir` (mesuré : mutation de la couche compacte → le corpus
    de la CI rougit). Ce qu'elle n'exerçait pas, c'est l'espacement DÉLIBÉRÉ — « sui
    cide » — c'est-à-dire quelqu'un qui contourne un filtre, ou qui hésite en écrivant.
    """
    # 🔴 PREMIER FILTRE : « contient suicid, et un espace quelque part ». Il acceptait
    # « je veux me suicider » — une phrase parfaitement ordinaire — et restait donc VERT
    # quand on retirait `sui cide` du script. Il nommait l'espacement délibéré sans le
    # chercher. Ce qui le définit vraiment : le mot n'est PAS là en entier, il ne
    # réapparaît qu'une fois la ponctuation et les espaces retirés.
    compactes = [
        p for p, attendu in _cas_du_script()
        if attendu
        and "suicid" not in p.lower()
        and "suicid" in re.sub(r"[^a-z]", "", p.lower())
    ]

    assert compactes, "au moins une phrase doit exercer la couche des formes compactes"
    for phrase in compactes:
        assert detect_crisis(phrase), phrase
