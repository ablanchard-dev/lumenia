"""Tout texte du serveur qui porte le 3114 s'écrit en français correct.

23/09/2026 — repasse de la grille d'audit : le refus sans identifiant (401) disait « En cas de
detresse », le refus d'un outil fermé « parcours d'entree valide », la page d'erreur « Ca a casse de
notre cote… Reessaie », l'anti-spam « Si ca urge… repond ». Ce sont les phrases qu'on lit dans les
moments où quelque chose ne va pas, et elles portent le numéro de prévention du suicide. Le refus du
chat avait été corrigé seul (c17687a) : ce garde tient toute la famille, lue dans l'arbre du code.
"""
import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
SANS_ACCENT = re.compile(r"\b(detresse|entree|Reessaie|reessaie|Ca a casse|cote|ca urge|repond|valide\.)", re.I)


def _textes_du_3114():
    for module in sorted(APP.glob("*.py")):
        arbre = ast.parse(module.read_text(encoding="utf-8-sig"))  # un module porte un BOM
        # Les docstrings (chaînes posées seules) sont des notes pour le code, pas des phrases affichées.
        notes = {id(n.value) for n in ast.walk(arbre) if isinstance(n, ast.Expr)}
        for noeud in ast.walk(arbre):
            if id(noeud) in notes:
                continue
            if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str) and "3114" in noeud.value:
                yield f"{module.name}:{noeud.lineno}", noeud.value


def test_le_crible_voit_bien_les_textes_du_3114():
    assert len(list(_textes_du_3114())) >= 4, "témoin : les refus et l'anti-spam doivent être lus"


def test_aucun_texte_du_3114_ne_perd_ses_accents():
    fautifs = [f"{ou} : « {m.group(0)} »" for ou, texte in _textes_du_3114() for m in [SANS_ACCENT.search(texte)] if m]
    assert fautifs == [], f"textes du 3114 sans accents : {fautifs}"
