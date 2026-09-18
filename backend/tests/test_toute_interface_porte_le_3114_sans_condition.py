# -*- coding: utf-8 -*-
"""Le 3114 ne se mérite pas.

18/09/2026. Deux tests gardent déjà le numéro de crise sur l'interface servie :
il y est toujours, et il y reste même quand le reste tombe en panne. Mesure du
jour sur l'**autre** interface du dépôt, `frontend/app.py` (Streamlit) :

    risk_flag = api_get("/risk").get("risk_flag", False)
    if risk_flag:
        st.error("... En cas d'urgence : 3114 / 15 / 112.")

C'est la seule occurrence du numéro dans tout le fichier. Il n'apparaît donc
qu'après qu'un PHQ-9 a levé un signal. Quelqu'un qui ouvre l'application en
détresse sans avoir passé de questionnaire ne le voit **nulle part** — et vingt
lignes plus haut, un `st.stop()` sur le consentement coupe la page avant même
d'en arriver là.

Le README dit que cette interface n'est « plus utilisée, gardée pour
référence ». Le dépôt dit autre chose : `docker-compose.yml` la construit et la
lance, et `run_frontend.bat` comme `setup_windows_frontend.ps1` attendent un
double-clic à la racine. C'est la phrase qui promet qui est en retard sur le
dépôt, pas l'inverse — et en attendant, une interface de santé mentale
atteignable montre le numéro de crise sous condition.

Ce fichier ne juge pas si cette interface doit rester : ce n'est pas au test de
trancher. Il exige seulement que **toute** interface du dépôt qui connaît le
3114 le donne au moins une fois sans condition.
"""
import ast
from pathlib import Path

import pytest

DEPOT = Path(__file__).resolve().parent.parent.parent
NUMERO = "3114"


def _interfaces() -> list[Path]:
    """Les interfaces Python du dépôt, hors backend : ce que quelqu'un peut lancer."""
    return sorted(
        f for f in DEPOT.glob("*/*.py")
        if "backend" not in f.parts and NUMERO in f.read_text(encoding="utf-8-sig")
    )


def _hors_condition(source: str) -> bool:
    """Le numéro apparaît-il au moins une fois hors de tout `if` / `try` / `except` ?

    On marche l'arbre en gardant la profondeur conditionnelle : une chaîne posée
    sous un `if` n'est montrée que si la condition est vraie, et c'est exactement
    ce qu'on refuse ici.
    """
    def parcourir(noeud, sous_condition: bool) -> bool:
        if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
            if NUMERO in noeud.value and not sous_condition:
                return True

        for champ, valeur in ast.iter_fields(noeud):
            # Le TEST d'un `if` n'est pas son corps : `if "3114" in x` ne montre rien.
            conditionne = sous_condition or (
                isinstance(noeud, (ast.If, ast.IfExp, ast.While, ast.Try, ast.ExceptHandler))
                and champ in ("body", "orelse", "handlers", "finalbody", "test")
            )
            for enfant in (valeur if isinstance(valeur, list) else [valeur]):
                if isinstance(enfant, ast.AST) and parcourir(enfant, conditionne):
                    return True
        return False

    return parcourir(ast.parse(source), False)


def test_le_crible_voit_bien_une_interface_a_verifier():
    """Témoin de contenu : sans lui, un chemin changé rendrait le garde muet."""
    interfaces = _interfaces()

    assert interfaces, "aucune interface trouvée hors backend : le crible ne lit rien"
    assert any(f.name == "app.py" for f in interfaces), [f.name for f in interfaces]


def test_l_analyseur_distingue_une_mention_conditionnelle_d_une_autre():
    """Témoin inverse : sans lui, un analyseur toujours vrai passerait tout."""
    assert _hors_condition('st.write("En cas d\'urgence : 3114")')
    assert not _hors_condition('if risque:\n    st.error("urgence : 3114")')
    assert not _hors_condition('try:\n    x()\nexcept Exception:\n    st.write("3114")')


@pytest.mark.parametrize("interface", _interfaces(), ids=lambda f: f.parent.name)
def test_chaque_interface_donne_le_3114_sans_condition(interface):
    assert _hors_condition(interface.read_text(encoding="utf-8-sig")), (
        f"{interface.relative_to(DEPOT)} ne montre le 3114 que sous condition. "
        "Quelqu'un qui ouvre cette interface en détresse sans remplir de questionnaire "
        "ne le voit nulle part. Sur l'interface servie, c'est la garantie qu'on tient "
        "depuis le début : le numéro ne se mérite pas"
    )
