# -*- coding: utf-8 -*-
"""Le script du front ne doit poser aucun style que notre propre CSP interdit.

Trouvé le 17/09/2026 en ouvrant l'application et en lisant la console — pas en
relisant le code. La CSP posée au tour 2 (`style-src 'self'`) bloque **les
attributs** `style="..."`, y compris ceux fabriqués dans une chaîne HTML. Or
`app.js` en posait un seul : celui qui remplit la **barre de progression du
parcours d'entrée**.

Conséquence concrète : pendant le test cognitif d'entrée, la barre restait vide.
Pour des profils TDAH et autistes, savoir où l'on en est dans une épreuve n'est
pas de la décoration.

Ce que ce test ne fait pas : exécuter le script. Il interdit la **forme** qui
échoue, ce qui suffit à empêcher le retour du défaut. Assigner `el.style.width`
(la propriété DOM) reste permis par la CSP et n'est donc pas visé.
"""
import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "static" / "app.js"
CODE = SCRIPT.read_text(encoding="utf-8")


def test_le_script_ne_fabrique_aucun_attribut_style():
    # Une ligne de commentaire peut citer la forme interdite pour l'expliquer :
    # c'est le cas juste au-dessus du correctif. On lit le code, pas les commentaires.
    interdit = re.compile(r'style\s*=\s*["\']|setAttribute\(\s*["\']style["\']|\.cssText')
    fautifs = [
        (i, l.strip()[:110])
        for i, l in enumerate(CODE.splitlines(), 1)
        if not l.strip().startswith(("//", "*", "/*")) and interdit.search(l)
    ]
    assert fautifs == [], fautifs


def test_la_barre_de_progression_se_remplit_bien_par_la_propriete():
    """La garantie positive : sans elle, supprimer la barre ferait passer le test
    précédent tout en laissant la personne sans repère."""
    assert re.search(r"p-bar-fill", CODE), "la barre de progression a disparu du script"
    assert re.search(r"\.style\.width\s*=", CODE), (
        "la largeur doit être posée par la propriété DOM, que la CSP autorise")
