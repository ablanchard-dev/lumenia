# -*- coding: utf-8 -*-
"""La détresse écrite dans un champ libre reçoit une réponse de détresse.

18/09/2026. Le dépôt a déjà payé cette leçon le 17/09 : « je veux mourir, aide
moi » envoyé à `/focus/decompose` repartait au LLM et revenait en décomposition
de tâche, sans le 3114. La correction a couvert **les routes qui appellent le
LLM**, et un crible déduit cet ensemble de l'AST pour qu'aucune n'y échappe.

`/entry/verify` n'appelle aucun LLM pour les épreuves objectives. Elle est donc
restée dehors. Mesure du jour, sur une vraie épreuve du parcours :

    POST /entry/verify {"answer": "je veux mourir, je ne vois plus de raison
                                   de continuer"}
    200 {"ok": false, "hint": "Regarde ce qu'on ajoute à chaque pas : +1, +2, +3…"}

Le même texte envoyé au journal déclenche la réponse de crise complète.

**C'est le pire endroit où rater ça.** La personne n'a pas encore accès au chat —
le gate est fermé tant que le parcours n'est pas validé. Elle passe un test
cognitif éliminatoire, elle écrit ce qu'elle a, et l'application lui répond un
indice d'arithmétique. Si elle échoue, l'écran suivant lui dit « le seuil reste
fermé ».

Le crible ne liste aucune route : il déduit des schémas quels champs portent du
**texte libre**, puis vérifie que chaque route qui en reçoit passe par le garde.
Un champ est libre quand il est requis et accepte au moins 200 caractères : les
menus du produit (`pacing`, `style`, `mode`) sont bornés à 40, les identifiants à
120. Ce seuil est le seul réglage du fichier, et il est mesuré, pas choisi.
"""
import ast
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

APP = Path(__file__).resolve().parent.parent / "app"
client = TestClient(app)

DETRESSE = "je veux mourir, je ne vois plus de raison de continuer"
SEUIL_TEXTE_LIBRE = 200


def _schemas_a_texte_libre() -> set[str]:
    """Les modèles qui portent au moins un champ de texte libre."""
    source = (APP / "schemas.py").read_text(encoding="utf-8-sig")
    # Les alias de longueur du module, pour résoudre `TexteCourt`/`TexteLong`.
    alias = {
        nom: int(borne.replace("_", ""))
        for nom, borne in re.findall(r"^(\w+)\s*=\s*Annotated\[str,\s*Field\(max_length=([\d_]+)\)\]",
                                     source, re.M)
    }
    porteurs = set()
    for nom, corps in re.findall(r"^class (\w+)\(BaseModel\):((?:\n(?:    .*)?)+)", source, re.M):
        for ligne in corps.splitlines():
            champ = ligne.strip()
            if not champ or champ.startswith("#"):
                continue
            # Un champ avec valeur par défaut n'est pas une saisie qu'on impose.
            longueur = None
            for a, borne in alias.items():
                if re.search(rf":\s*{a}\s*$", champ):
                    longueur = borne
            m = re.search(r"max_length=([\d_]+)", champ)
            if m:
                defaut = re.search(r"Field\(\s*(?!\.\.\.)[^)]", champ)
                if defaut:
                    continue
                longueur = int(m.group(1).replace("_", ""))
            if longueur and longueur >= SEUIL_TEXTE_LIBRE:
                porteurs.add(nom)
    return porteurs


def _routes_a_texte_libre() -> list[tuple[str, str, bool]]:
    """(chemin, schéma, passe par le garde) pour chaque route qui reçoit du texte libre."""
    porteurs = _schemas_a_texte_libre()
    arbre = ast.parse((APP / "main.py").read_text(encoding="utf-8-sig"))
    trouvees = []
    for noeud in arbre.body:
        if not isinstance(noeud, ast.FunctionDef):
            continue
        chemin = next(
            (d.args[0].value for d in noeud.decorator_list
             if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "post" and d.args),
            None,
        )
        if chemin is None:
            continue
        schemas = [a.annotation.id for a in noeud.args.args
                   if isinstance(getattr(a, "annotation", None), ast.Name)]
        libre = next((s for s in schemas if s in porteurs), None)
        if libre is None:
            continue
        corps = ast.dump(noeud)
        trouvees.append((chemin, libre, "_guard" in corps or "detect_crisis" in corps))
    return trouvees


def test_le_crible_voit_bien_des_champs_libres_et_ecarte_les_menus():
    """Témoin de contenu ET témoin inverse : ce qu'il voit, et ce qu'il refuse de voir."""
    porteurs = _schemas_a_texte_libre()

    assert "ChatIn" in porteurs and "JournalIn" in porteurs, porteurs
    assert "EntryVerifyIn" in porteurs, "la réponse au parcours EST une saisie libre"
    # Les menus et les identifiants ne sont pas du texte libre : les accuser ferait
    # crier au loup, et un crible qui crie au loup finit désactivé.
    assert "ProfileIn" not in porteurs, "low_stim / font_size / pacing sont des réglages"
    assert "EntryAssessmentIn" not in porteurs, "des clés de dimension, pas une saisie"


def test_le_crible_voit_bien_des_routes():
    routes = _routes_a_texte_libre()

    assert len(routes) >= 5, routes
    assert any(c == "/entry/verify" for c, _, _ in routes), routes


@pytest.mark.parametrize("chemin,schema,garde", _routes_a_texte_libre(),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_chaque_route_a_texte_libre_passe_par_le_garde(chemin, schema, garde):
    assert garde, (
        f"{chemin} reçoit du texte libre ({schema}) sans passer par la détection de "
        "détresse. Le 17/09, cette même faute sur /focus/decompose renvoyait une "
        "décomposition de tâche à « je veux mourir » ; la correction n'a couvert que "
        "les routes qui appellent le LLM"
    )


def test_la_detresse_ecrite_dans_le_parcours_recoit_le_3114():
    """La preuve par l'exécution, sur une vraie épreuve du parcours."""
    parcours = client.get("/entry/parcours").json()
    epreuve = parcours["steps"][0]["id"]

    reponse = client.post("/entry/verify", json={"challenge_id": epreuve, "answer": DETRESSE}).json()

    assert "3114" in str(reponse), (
        f"quelqu'un écrit sa détresse dans le parcours d'entrée et reçoit : {reponse}. "
        "À ce moment-là le chat lui est encore fermé — c'est le seul endroit où elle "
        "peut écrire, et personne ne lit"
    )
