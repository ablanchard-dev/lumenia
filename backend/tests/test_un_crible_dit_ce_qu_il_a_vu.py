# -*- coding: utf-8 -*-
"""Un crible qui conclut « aucune faute » doit prouver qu'il a lu quelque chose.

18/09/2026. `test_aucun_test_ne_passe_sans_rien_prouver.py` refuse le test sans
la moindre assertion. Ce fichier vise le cran au-dessus : le test qui **affirme**,
mais sur un ensemble qui peut être vide sans que personne le sache.

Un module qui parcourt des fichiers et conclut `assert fautes == []` dit deux
choses très différentes selon ce qu'il a lu : « j'ai lu, c'est propre », ou « je
n'ai lu aucun fichier ». La seconde est verte aussi. Un chemin qui change, un
filtre trop strict, et le garde se tait pour toujours.

Mesure du jour, sans défaut trouvé : les seize modules concernés portent tous au
moins une assertion qui exige du contenu. La discipline était tenue à la main
depuis ce matin — elle n'était exigée nulle part.

Ce que ce crible **ne** fait **pas** : accuser toute conclusion au vide. Vérifier
qu'un parseur rend une liste vide sur une entrée vide se suffit à soi-même. Seul
le couple « je parcours des fichiers » et « je conclus au vide » ment en silence.
"""
import ast
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PARCOURT = re.compile(r"\.glob\(|\.rglob\(|iterdir\(|read_text\(")


def _conclut_au_vide(noeud: ast.Assert) -> bool:
    """`assert x == []`, `== {}` — la forme qui peut être vraie sur du néant."""
    test = noeud.test
    if not isinstance(test, ast.Compare) or not test.comparators:
        return False
    droite = test.comparators[0]
    if not isinstance(droite, (ast.List, ast.Dict, ast.Set)):
        return False
    return not getattr(droite, "elts", None) and not getattr(droite, "keys", None)


def _compter(source: str) -> tuple[int, int]:
    """(conclusions au vide, assertions qui exigent autre chose)."""
    arbre = ast.parse(source)
    vides = autres = 0
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Assert):
            if _conclut_au_vide(noeud):
                vides += 1
            else:
                autres += 1
    return vides, autres


def _modules_cribles() -> list[Path]:
    """Les modules de test qui lisent des fichiers ET concluent au vide."""
    trouves = []
    for fichier in sorted(TESTS.glob("test_*.py")):
        # utf-8-sig : certains modules portent un BOM, et `ast.parse` refuse le U+FEFF.
        source = fichier.read_text(encoding="utf-8-sig")
        if not PARCOURT.search(source):
            continue
        if _compter(source)[0]:
            trouves.append(fichier)
    return trouves


def test_le_crible_voit_bien_des_modules_a_verifier():
    """Le témoin de ce fichier-ci : il s'applique d'abord à lui-même."""
    modules = _modules_cribles()

    assert len(modules) >= 5, [m.name for m in modules]


def test_l_analyseur_distingue_une_conclusion_au_vide_d_un_temoin():
    """Témoin inverse. Un premier essai comptait par expression régulière et
    prenait `assert r.status_code == 200` pour une absence de témoin : deux faux
    positifs sur trois accusations. L'AST avant la conclusion."""
    vides, autres = _compter(
        "assert fautes == []\n"
        "assert r.status_code == 200\n"
        "assert len(vus) >= 3\n"
    )

    assert vides == 1
    assert autres == 2


def test_chaque_module_crible_prouve_qu_il_a_lu_quelque_chose():
    muets = [
        fichier.name
        for fichier in _modules_cribles()
        if _compter(fichier.read_text(encoding="utf-8-sig"))[1] == 0
    ]

    assert muets == [], (
        "ces modules parcourent des fichiers et concluent « aucune faute » sans jamais "
        f"affirmer avoir lu quelque chose : {muets}. Ajoutez un témoin de contenu — "
        "sinon un chemin qui change les rend verts sur zéro fichier, pour toujours"
    )
