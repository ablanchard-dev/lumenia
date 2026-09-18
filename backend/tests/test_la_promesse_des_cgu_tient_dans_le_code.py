# -*- coding: utf-8 -*-
"""Les CGU promettent une chose au client. Le code doit la tenir.

18/09/2026. Les CGU affirment, noir sur blanc : « Lumenia **n'est pas un
dispositif médical**. Il ne pose aucun diagnostic, ne prescrit rien. » Ce n'est
pas une formule de politesse — c'est ce qui sépare un compagnon cognitif d'un
produit qui aurait besoin d'un marquage CE.

Mesure du jour : la promesse est tenue, mais par **une seule ligne de texte**
dans `SYSTEM_PROMPT`, et par la discipline de faire passer chaque appel LLM par
là. Rien de structurel. Un `complete(...)` ajouté demain dans une nouvelle
fonctionnalité — un résumé, un coach, une reformulation — partirait sans
consigne, et le produit se mettrait à donner des avis médicaux sans qu'aucun
test ne rougisse. C'est le même défaut que le score côté DrDXT : ce que le
client lit n'était tenu par rien.

Ce fichier attache la phrase des CGU au code qui doit l'honorer.
"""
import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
APP = RACINE / "app"
STATIC = RACINE / "static"

# La consigne doit interdire le diagnostic ET le conseil médical : promettre
# l'un sans l'autre laisserait passer « à ta place je prendrais ce traitement ».
INTERDIT_LE_DIAGNOSTIC = re.compile(r"jamais\s+de\s+diagnostic", re.I)
INTERDIT_LE_CONSEIL = re.compile(r"pas\s+de\s+conseil\s+m[ée]dical", re.I)


def _source(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8-sig")


def _porte_une_consigne_systeme(fonction: ast.AST) -> bool:
    """Vrai si la fonction construit un message « system » bâti sur SYSTEM_PROMPT.

    On exige le dict littéral {"role": "system", "content": … SYSTEM_PROMPT …}
    plutôt que la simple présence du nom : une fonction peut mentionner
    SYSTEM_PROMPT dans un log sans jamais l'envoyer au modèle.
    """
    for noeud in ast.walk(fonction):
        if not isinstance(noeud, ast.Dict):
            continue
        paires = {
            cle.value: valeur
            for cle, valeur in zip(noeud.keys, noeud.values)
            if isinstance(cle, ast.Constant)
        }
        role, contenu = paires.get("role"), paires.get("content")
        if isinstance(role, ast.Constant) and role.value == "system" and contenu is not None:
            if "SYSTEM_PROMPT" in ast.unparse(contenu):
                return True
    return False


def _appels_au_modele():
    """Chaque appel à complete(...) dans app/, avec la fonction qui le contient."""
    for fichier in sorted(APP.glob("*.py")):
        arbre = ast.parse(_source(fichier))
        for fonction in ast.walk(arbre):
            if not isinstance(fonction, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for appel in ast.walk(fonction):
                if not isinstance(appel, ast.Call):
                    continue
                nom = appel.func.attr if isinstance(appel.func, ast.Attribute) else getattr(appel.func, "id", "")
                # `complete` exactement : entry_is_complete n'appelle pas de modèle.
                if nom == "complete":
                    yield fichier.name, fonction
                    break


def test_aucun_appel_au_modele_ne_part_sans_la_consigne():
    """Le garde structurel : la promesse tient au niveau de l'appel, pas du bon usage."""
    nus = sorted(
        {
            f"{nom_fichier} :: {fonction.name}"
            for nom_fichier, fonction in _appels_au_modele()
            if not _porte_une_consigne_systeme(fonction)
        }
    )
    assert nus == [], (
        "ces appels au modèle partent sans la consigne système : les CGU promettent "
        f"qu'aucun diagnostic n'est posé, ces chemins-là ne le garantissent pas — {nus}"
    )


def test_le_crible_voit_vraiment_les_appels_au_modele():
    """Témoin : un crible qui ne trouverait aucun appel serait vert sur le vide."""
    assert len({f"{f} :: {fn.name}" for f, fn in _appels_au_modele()}) >= 2


def test_le_crible_refuse_un_appel_sans_consigne():
    """Témoin inverse : il doit dire non, sinon il ne dit jamais rien."""
    avec = ast.parse(
        'def f():\n'
        '    return complete([{"role": "system", "content": SYSTEM_PROMPT}, u])\n'
    ).body[0]
    sans = ast.parse('def g():\n    return complete([{"role": "user", "content": m}])\n').body[0]
    journal = ast.parse('def h():\n    log.debug(SYSTEM_PROMPT)\n    return complete(m)\n').body[0]

    assert _porte_une_consigne_systeme(avec)
    assert not _porte_une_consigne_systeme(sans)
    assert not _porte_une_consigne_systeme(journal), "mentionner la consigne n'est pas l'envoyer"


def test_la_consigne_interdit_bien_le_diagnostic_et_le_conseil_medical():
    """La garantie positive : le garde ci-dessus ne vaut que si le texte tient."""
    from app.llm import SYSTEM_PROMPT

    assert INTERDIT_LE_DIAGNOSTIC.search(SYSTEM_PROMPT), SYSTEM_PROMPT
    assert INTERDIT_LE_CONSEIL.search(SYSTEM_PROMPT), SYSTEM_PROMPT


def test_les_cgu_et_le_code_disent_la_meme_chose():
    """Le lien : la phrase lue par le client et la règle appliquée au modèle
    doivent vivre ou mourir ensemble. Si les CGU cessent de le promettre, ce
    test le dit ; si le code cesse de le tenir, le test au-dessus le dit."""
    cgu = _source(STATIC / "cgu.html")
    assert "ne pose aucun diagnostic" in cgu
    assert "n'est pas un dispositif médical" in cgu
