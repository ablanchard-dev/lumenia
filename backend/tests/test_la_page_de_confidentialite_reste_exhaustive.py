# -*- coding: utf-8 -*-
"""« Exactement quatre tables » : une phrase qui doit rester vraie demain.

18/09/2026. La politique de confidentialité ne se contente pas de décrire, elle
affirme une **exhaustivité** : « une base locale qui contient exactement quatre
tables », puis les nomme. C'est ce qui permet à quelqu'un de savoir ce que le
serveur garde de lui — et c'est une promesse que le code peut démentir sans
qu'aucun test ne rougisse.

Elle l'avait déjà fait une fois : l'anti-spam gardait l'adresse IP en mémoire
sans que la page le dise (corrigé le matin même). Le paragraphe a été ajouté,
mais l'exhaustivité elle-même n'était toujours tenue par rien : une cinquième
table déclarée demain dans `app/models.py` rendrait la phrase fausse, en
silence, sur une application de santé mentale.

Le lien est vérifié **dans les deux sens**. Une table du code absente de la page,
c'est une collecte non déclarée. Une table nommée sur la page mais absente du
code, c'est une page qui parle d'autre chose que du produit — moins grave, aussi
faux.
"""
import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MODELS = RACINE / "app" / "models.py"
PAGE = RACINE / "static" / "confidentialite.html"

NOMBRES = {
    1: "une", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq",
    6: "six", 7: "sept", 8: "huit", 9: "neuf", 10: "dix",
}


def _tables_du_code() -> set[str]:
    """Les `__tablename__` déclarés, lus dans l'arbre syntaxique.

    L'AST plutôt qu'un grep : une chaîne « kv_store » citée dans un commentaire
    ou une requête ne déclare pas une table, et compter de travers ici rendrait
    le test bruyant — donc, tôt ou tard, ignoré.
    """
    # utf-8-sig : `models.py` porte un BOM, et `ast.parse` refuse le U+FEFF.
    arbre = ast.parse(MODELS.read_text(encoding="utf-8-sig"))
    noms = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign):
            continue
        cibles = {c.id for c in noeud.targets if isinstance(c, ast.Name)}
        if "__tablename__" in cibles and isinstance(noeud.value, ast.Constant):
            noms.add(noeud.value.value)
    return noms


def _texte_de_la_page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_le_crible_voit_bien_les_tables_du_code():
    """Témoin : un crible qui ne trouve rien rendrait tout le reste vert sur le vide."""
    tables = _tables_du_code()

    assert len(tables) >= 3, tables
    assert "journal" in tables


def test_chaque_table_du_code_est_nommee_sur_la_page():
    page = _texte_de_la_page()

    tues = sorted(t for t in _tables_du_code() if t not in page)

    assert tues == [], (
        "ces tables existent dans le code et ne sont nommées nulle part sur la page qui "
        f"prétend les lister toutes : {tues}. Sur une application de santé mentale, une "
        "collecte non déclarée n'est pas un oubli de documentation"
    )


def test_la_page_ne_nomme_aucune_table_qui_n_existe_plus():
    """L'autre sens : une page qui décrit un produit qui n'est plus celui-là."""
    page = _texte_de_la_page()
    reelles = _tables_du_code()

    citees = set(re.findall(r"<code>([a-z_]+)</code>", page))
    fantomes = sorted(c for c in citees if c not in reelles)

    assert fantomes == [], f"la page nomme des tables absentes du code : {fantomes}"


def test_le_compte_annonce_par_la_page_est_le_bon():
    """La phrase porte un nombre écrit en toutes lettres : il doit suivre le code."""
    attendu = NOMBRES[len(_tables_du_code())]
    page = _texte_de_la_page()

    m = re.search(r"exactement\s+(\w+)\s+tables", page)
    assert m, "la page n'affirme plus d'exhaustivité — si c'est voulu, ce test doit changer aussi"

    assert m.group(1) == attendu, (
        f"la page annonce « exactement {m.group(1)} tables » et le code en déclare "
        f"{len(_tables_du_code())} ({attendu})"
    )
