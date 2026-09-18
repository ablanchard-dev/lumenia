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


# ---------------------------------------------------------------------------
# 18/09/2026, plus tard dans la journée — LE CAS SUIVANT : L'ASSERTION EXISTE,
# MAIS ELLE NE S'EXÉCUTE JAMAIS.
#
# Le crible du dessus ferme le cas grossier (aucune assertion). Le tour 112 côté
# DrDXT a montré le cas d'après, et il est plus courant : un test qui affirme
# **dans une boucle**, sur une collection qu'il est allé chercher. Si la collection
# ressort vide — un `glob` qui ne trouve plus rien, un parseur dont le motif ne mord
# plus, une banque filtrée sur un `kind` renommé — la boucle ne tourne pas, aucune
# assertion ne s'exécute, et le test est **vert**. Il annonce une garantie qu'il n'a
# pas regardée.
#
# C'est le même défaut que « un test peut nommer une garantie sans la tenir »,
# déplacé d'un cran : ici l'assertion est bien écrite, elle est simplement
# inatteignable.
#
# Ce que le crible exige : quand une boucle affirme sur une collection **dérivée**
# (le résultat d'un appel, d'un attribut, d'une compréhension — bref, quelque chose
# que le produit ou le dépôt fabrique), le test doit aussi porter un **témoin de
# non-vacuité** : une assertion qui échoue si la collection est vide.
#
# Ce qu'il n'exige PAS, mesuré avant de l'écrire :
#   * les collections littérales (`for c in ["/", "/cgu"]`) et les constantes de
#     module qui sont des littéraux : non vides par construction ;
#   * `range(...)`, qui ne dépend de rien qu'on puisse casser par inadvertance.
# Avec ces deux exclusions : 8 accusations sur 292 fonctions, dont 6 réelles, et
# les deux restantes étaient des `range(...)` — d'où l'exclusion.
# ---------------------------------------------------------------------------


def _constantes_litterales(arbre) -> set[str]:
    """Les noms de module assignés à une liste/tuple/dict/ensemble écrit en toutes lettres."""
    noms: set[str] = set()
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and isinstance(
            noeud.value, (ast.List, ast.Tuple, ast.Set, ast.Dict)
        ):
            noms.update(c.id for c in noeud.targets if isinstance(c, ast.Name))
    return noms


def _iterables_derives(fonction, litterales: set[str]) -> list[str]:
    """Les collections *fabriquées* sur lesquelles la fonction affirme."""
    derives = []
    for noeud in ast.walk(fonction):
        if not isinstance(noeud, (ast.For, ast.AsyncFor)):
            continue
        if not any(isinstance(s, ast.Assert) for s in ast.walk(noeud)):
            continue

        source = noeud.iter
        if isinstance(source, ast.Name) and source.id in litterales:
            continue
        if isinstance(source, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            continue
        texte = ast.unparse(source)
        if texte.startswith("range("):
            continue
        derives.append(texte)
    return derives


def _porte_un_temoin_de_non_vacuite(fonction) -> bool:
    """Une assertion qui tombe si la collection est vide."""
    for noeud in ast.walk(fonction):
        if not isinstance(noeud, ast.Assert):
            continue
        texte = ast.unparse(noeud.test)
        if "len(" in texte or texte.startswith("any(") or " in " in texte:
            return True
        if isinstance(noeud.test, ast.Name):  # `assert lignes`
            return True
    return False


def _accusations() -> list[str]:
    fautives = []
    for fichier in sorted(DOSSIER.glob("test_*.py")):
        # utf-8-sig : trois fichiers de tests portent un BOM, et `ast.parse` le refuse.
        arbre = ast.parse(fichier.read_text(encoding="utf-8-sig"))
        litterales = _constantes_litterales(arbre)
        for noeud in ast.walk(arbre):
            if not (isinstance(noeud, ast.FunctionDef) and noeud.name.startswith("test")):
                continue
            derives = _iterables_derives(noeud, litterales)
            if derives and not _porte_un_temoin_de_non_vacuite(noeud):
                fautives.append(f"{fichier.name}::{noeud.name} (sur {derives})")
    return fautives


def test_une_boucle_qui_affirme_sur_du_vide_ne_prouve_rien():
    """Sans témoin, une collection qui se vide rend le test vert et la garantie muette."""
    fautives = _accusations()

    assert not fautives, (
        "ces tests affirment dans une boucle sur une collection qu'ils sont allés "
        "chercher, sans jamais vérifier qu'elle n'est pas vide :\n  "
        + "\n  ".join(fautives)
    )


def test_le_crible_VOIT_une_boucle_sans_temoin():
    """Un crible qu'on ne peut pas faire tomber sur commande ne prouve rien."""
    faux = ast.parse(
        "def test_x():\n"
        "    for p in trouver_les_pages():\n"
        "        assert p.ok\n"
    )
    fonction = faux.body[0]

    assert _iterables_derives(fonction, set()) == ["trouver_les_pages()"]
    assert _porte_un_temoin_de_non_vacuite(fonction) is False


def test_le_crible_accepte_le_meme_test_AVEC_son_temoin():
    """Le contrepoids : ajouter le témoin doit suffire à sortir de l'accusation."""
    bon = ast.parse(
        "def test_x():\n"
        "    pages = trouver_les_pages()\n"
        "    assert len(pages) >= 3\n"
        "    for p in pages:\n"
        "        assert p.ok\n"
    )

    assert _porte_un_temoin_de_non_vacuite(bon.body[0]) is True


def test_une_collection_ecrite_en_toutes_lettres_n_est_pas_accusee():
    """Deuxième contrepoids : `for c in ['/', '/cgu']` ne peut pas se vider tout seul."""
    litteral = ast.parse(
        "def test_x():\n"
        "    for c in ['/', '/cgu']:\n"
        "        assert c\n"
    )
    boucle_range = ast.parse(
        "def test_x():\n"
        "    for i in range(20):\n"
        "        assert i >= 0\n"
    )

    assert _iterables_derives(litteral.body[0], set()) == []
    assert _iterables_derives(boucle_range.body[0], set()) == []
