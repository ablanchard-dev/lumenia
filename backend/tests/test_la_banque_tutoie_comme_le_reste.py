"""Les épreuves tutoient, comme tout le reste de Lumenia.

23/09/2026 — le produit tutoie partout (« Prends ton temps », « Ta réponse »), mais 242 des 300
épreuves de la banque vouvoyaient (« Dites en quoi… Choisissez… ») : la personne changeait de
registre d'une ligne à l'autre de la même carte. Aucun document ne justifiait le vouvoiement.
"""
import json
import re
from pathlib import Path

BANQUE = Path(__file__).resolve().parent.parent / "app" / "entry_bank.json"
VOUS = re.compile(r"\b(vous|votre|vos|dites|faites)\b|\b\w{3,}ez\b", re.I)
PAS_UN_VERBE = {"chez", "assez", "nez", "rez"}


def test_aucune_epreuve_ne_vouvoie():
    banque = json.loads(BANQUE.read_text(encoding="utf-8"))
    items = [it for d in banque for it in d["pool"]]
    assert len(items) >= 290, "témoin : la banque doit être lue en entier"
    fautifs = [f"{it['id']}.{champ}" for it in items for champ in ("consigne", "question", "explication")
               if isinstance(it.get(champ), str)
               and any(m.group(0).lower() not in PAS_UN_VERBE for m in VOUS.finditer(it[champ]))]
    assert fautifs == [], f"{len(fautifs)} textes vouvoient encore, ex. {fautifs[:5]}"
