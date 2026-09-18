# -*- coding: utf-8 -*-
"""Un test qui n'affirme rien passe quoi qu'il arrive au produit.

18/09/2026. La journée a montré cinq fois la même chose, des deux côtés du projet :
**un test peut nommer une garantie sans la tenir**. Ici on ferme le cas extrême,
celui qui se détecte mécaniquement — un test sans la moindre assertion occupe la
place d'une garantie sans en être une.

État mesuré à l'écriture : 144 fonctions de test, **aucune sans preuve**.

Le crible lit l'arbre syntaxique plutôt que le texte : un `assert`, un `raise`,
un `pytest.raises(...)`, un `pytest.fail(...)` comptent — et un test qui délègue
à une fonction d'aide du module ou de `conftest.py` compte aussi, parce que
l'assertion y vit. Sans ce dernier point, le crible accuserait des tests
parfaitement sains ; c'est arrivé côté DrDXT, où la première version en désignait
quatorze, dont quatre tests de sécurité de licence.
"""
import ast
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
PLANCHER = 100  # 144 le jour de l'écriture ; ce test doit rougir bien avant d'être vide


class _ChercheUnePreuve(ast.NodeVisitor):
    """Vrai dès qu'un nœud affirme quelque chose."""

    def __init__(self) -> None:
        self.trouve = False

    def visit_Assert(self, noeud):  # noqa: N802 (nom impose par ast)
        self.trouve = True

    def visit_Raise(self, noeud):  # noqa: N802
        self.trouve = True

    def visit_Call(self, noeud):  # noqa: N802
        nom = ast.unparse(noeud.func)
        if any(mot in nom for mot in ("raises", "fail", "approx", "warns", "deprecated_call")):
            self.trouve = True
        self.generic_visit(noeud)


def _prouve(noeud) -> bool:
    chercheur = _ChercheUnePreuve()
    chercheur.visit(noeud)
    return chercheur.trouve


def _aides_qui_prouvent(arbre) -> set[str]:
    """Les fonctions d'aide du module qui portent elles-mêmes une assertion."""
    return {
        n.name
        for n in ast.walk(arbre)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("test")
        and _prouve(n)
    }


def _fonctions_de_test():
    conftest = ast.parse((DOSSIER / "conftest.py").read_text(encoding="utf-8-sig"))
    aides_communes = _aides_qui_prouvent(conftest)

    for fichier in sorted(DOSSIER.glob("test_*.py")):
        arbre = ast.parse(fichier.read_text(encoding="utf-8-sig"))
        aides = _aides_qui_prouvent(arbre) | aides_communes
        for noeud in ast.walk(arbre):
            if isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)) and noeud.name.startswith("test"):
                yield fichier.name, noeud, aides


def test_aucun_test_ne_passe_sans_rien_affirmer():
    creux = []
    for nom_fichier, noeud, aides in _fonctions_de_test():
        if _prouve(noeud):
            continue
        appelees = {
            ast.unparse(appel.func).split(".")[-1]
            for appel in ast.walk(noeud)
            if isinstance(appel, ast.Call)
        }
        if appelees & aides:
            continue
        creux.append(f"{nom_fichier} :: {noeud.name}")

    assert creux == [], f"tests sans aucune assertion : {creux}"


def test_le_crible_lit_vraiment_la_suite():
    """Témoin indispensable : un crible qui ne trouverait aucun test rendrait le
    test précédent vert à jamais, en annonçant une garantie sur le vide."""
    assert sum(1 for _ in _fonctions_de_test()) >= PLANCHER


def test_le_crible_sait_reconnaitre_une_preuve_et_son_absence():
    """Témoin inverse : il doit dire non sur un corps vide, et oui sur chaque
    forme d'assertion employée ici — sinon il pourrait n'en reconnaître aucune."""
    def _arbre(code):
        return ast.parse(code).body[0]

    assert not _prouve(_arbre("def test_creux():\n    x = 1 + 1\n"))
    assert _prouve(_arbre("def test_a():\n    assert True\n"))
    assert _prouve(_arbre("def test_b():\n    with pytest.raises(ValueError):\n        pass\n"))
    assert _prouve(_arbre("def test_c():\n    pytest.fail('non')\n"))
    assert _prouve(_arbre("def test_d():\n    raise AssertionError\n"))
