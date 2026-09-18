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


# ---------------------------------------------------------------------------
# 18/09/2026 — la MÊME affirmation vit dans le README, et personne ne la gardait.
#
# La page de confidentialité est exacte : elle nomme les quatre tables, et les
# trois tests ci-dessus la tiennent. Le README, lui, annonce « **Three** things do
# persist server-side » et en énumère trois : réponses du parcours, drapeau de
# risque, entrées de journal. Il oublie `profiles`.
#
# Ce ne sont « que » des préférences — mode faible stimulation, taille de police,
# rythme. Mais sur une application destinée à des personnes neuroatypiques, dire
# qu'on ne stocke pas ça alors qu'on le stocke, c'est précisément le genre de
# détail qui compte : `low_stim` est une information sur quelqu'un, pas un thème
# clair/sombre. Et l'affirmation est CHIFFRÉE, donc vérifiable, donc fausse.
#
# Deux surfaces portaient la promesse, une seule était gardée — le même trou que
# celui trouvé le même jour sur la version de Python annoncée.
# ---------------------------------------------------------------------------
README = RACINE.parent / "README.md"

# « Three things do persist » : le nombre est écrit en anglais, en toutes lettres.
NOMBRES_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def test_le_compte_annonce_par_le_readme_est_le_bon():
    texte = README.read_text(encoding="utf-8-sig")
    attendu = NOMBRES_EN[len(_tables_du_code())]

    m = re.search(r"(\w+)\s+things\s+do\s+persist", texte, re.I)
    assert m, "le README n'affirme plus d'exhaustivité — si c'est voulu, ce test doit changer aussi"

    assert m.group(1).lower() == attendu, (
        f"le README annonce « {m.group(1)} things do persist » et le code déclare "
        f"{len(_tables_du_code())} tables ({attendu}). Une affirmation chiffrée sur ce "
        "qui est stocké est une affirmation RGPD : trop basse, elle rassure à tort"
    )


def test_le_readme_nomme_ce_qui_persiste_vraiment():
    """Le compte ne suffit pas : encore faut-il que la liste dise quoi.

    Premier essai : chercher les mots dans tout le README. Il ne mordait pas —
    retirer « display preferences » de la phrase laissait le test vert, parce que
    le mot vit ailleurs dans le document. Le test nommait la garantie sans la
    tenir. On lit désormais le seul passage qui porte l'affirmation.
    """
    texte = README.read_text(encoding="utf-8-sig")
    # On recolle AVANT de chercher : le README passe à la ligne au milieu de sa
    # phrase, « Four things do » finit une ligne et « persist » commence la suivante.
    passage = next(
        (p for p in (" ".join(b.split()) for b in re.split(r"\n\s*\n", texte))
         if "do persist" in p),
        None,
    )
    assert passage, "le passage qui affirme ce qui persiste a disparu du README"

    for attendu in ("journal", "risk flag", "preference"):
        assert attendu in passage.lower(), (
            f"la phrase du README ne dit plus que « {attendu} » persiste côté serveur ; "
            f"le compte peut être juste et la liste muette — {passage}"
        )
