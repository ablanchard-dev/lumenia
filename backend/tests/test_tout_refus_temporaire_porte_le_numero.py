# -*- coding: utf-8 -*-
"""Un refus qui arrive AVANT le garde de crise est le seul à ne pas porter le numéro.

19/09/2026. Quatre endroits promettent la même chose, au présent et sans réserve :

  - les CGU, lues par le client : « Un refus temporaire renvoie toujours, lui aussi,
    les numéros d'urgence » ;
  - l'en-tête de `app/limite.py` : « Ce qu'elle s'interdit : faire taire le 3114. La
    reponse 429 porte le numero » ;
  - le commentaire du gestionnaire de panne, dans `app/web.py` : « il est sur tous les
    ecrans et dans la reponse 429 de l'anti-spam » ;
  - et un test, qui s'appelle `test_le_429_porte_toujours_le_3114`.

🔴 Mesuré aujourd'hui : le middleware émet **deux** réponses 429, et une seule porte le
numéro. `TROP_VITE` (routes LLM) le porte ; `TROP_D_ECRITURES`, ajouté le 18/09 pour le
budget des écritures, ne le porte pas.

Le test existant ne pouvait pas le voir, par construction : il envoie `POST /chat`
`PAR_MINUTE + 1` fois et lit `json()["reply"]`. Il n'atteint jamais l'autre branche du
middleware, et la clef qu'il lit n'existe pas dans l'autre corps. Son nom dit « toujours »,
sa mesure dit « sur cette route-là ». **Un test peut NOMMER une garantie sans la prouver.**

Ce que ça coûte, concrètement, et c'est le pire endroit possible : `POST /journal` n'est
pas gardé — écrire n'appelle aucun modèle — et le code de la route fait passer le titre et
le contenu par `_guard(...)`, exactement comme le chat. Quelqu'un qui écrit sa détresse
dans son journal reçoit donc le 3114. Sauf au-delà du quota d'écritures : là le refus
tombe dans le middleware, **avant** que la route ne s'exécute, donc avant le garde de
crise — et c'est la seule réponse du produit où le numéro manque.

Ce fichier ne liste aucune route : il DÉDUIT les corps des 429 en lisant `app/`, et exige
le numéro dans chacun.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import limite
from app.main import app

RACINE = Path(__file__).resolve().parent.parent
APP = RACINE / "app"
STATIC = RACINE / "static"
NUMERO = "3114"


def _constantes_du_module(arbre: ast.Module) -> dict[str, str]:
    """Les chaînes nommées au niveau du module — `TROP_VITE = "..."`."""
    valeurs: dict[str, str] = {}
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and len(noeud.targets) == 1:
            cible = noeud.targets[0]
            if isinstance(cible, ast.Name):
                try:
                    valeur = ast.literal_eval(noeud.value)
                except Exception:
                    continue
                if isinstance(valeur, str):
                    valeurs[cible.id] = valeur
    return valeurs


def _texte_du_corps(noeud: ast.AST, constantes: dict[str, str]) -> str:
    """Tout ce qui, dans ce corps de réponse, arrivera chez la personne sous forme de texte.

    On résout les noms : le corps s'écrit `{"reply": TROP_VITE}`, et c'est la constante
    qui porte — ou non — le numéro.
    """
    morceaux: list[str] = []
    for sous in ast.walk(noeud):
        if isinstance(sous, ast.Constant) and isinstance(sous.value, str):
            morceaux.append(sous.value)
        elif isinstance(sous, ast.Name) and sous.id in constantes:
            morceaux.append(constantes[sous.id])
    return "\n".join(morceaux)


def refus_temporaires(source: str, etiquette: str) -> list[tuple[str, str]]:
    """(d'où ça vient, ce que la personne lit) pour chaque réponse 429 construite ici."""
    arbre = ast.parse(source)
    constantes = _constantes_du_module(arbre)
    trouves: list[tuple[str, str]] = []

    for appel in ast.walk(arbre):
        if not isinstance(appel, ast.Call):
            continue
        est_429 = any(
            mot.arg == "status_code"
            and isinstance(mot.value, ast.Constant)
            and mot.value.value == 429
            for mot in appel.keywords
        )
        if not est_429 or not appel.args:
            continue
        trouves.append(
            (f"{etiquette}:{appel.lineno}", _texte_du_corps(appel.args[0], constantes))
        )
    return trouves


def _tous_les_refus() -> list[tuple[str, str]]:
    refus: list[tuple[str, str]] = []
    for fichier in sorted(APP.glob("*.py")):
        refus += refus_temporaires(fichier.read_text(encoding="utf-8-sig"), fichier.name)
    return refus


@pytest.fixture(autouse=True)
def _compteurs_vierges():
    limite.reset()
    yield
    limite.reset()


def test_le_crible_voit_bien_plusieurs_refus():
    """Témoin : un crible qui n'en trouverait aucun serait vert sur le vide."""
    refus = _tous_les_refus()

    assert len(refus) >= 2, refus
    assert all(texte.strip() for _, texte in refus), (
        "un corps dont le texte ne se résout pas ne prouve rien : " f"{refus}"
    )


def test_le_crible_sait_dire_non():
    """Témoin inverse : sur un refus muet, il doit rougir — sinon il ne dit jamais rien."""
    muet = "MESSAGE = 'ca repart dans une minute'\n" "x = JSONResponse({'detail': MESSAGE}, status_code=429)\n"
    parlant = (
        "MESSAGE = 'ca repart dans une minute, et le 3114 repond tout de suite'\n"
        "x = JSONResponse({'detail': MESSAGE}, status_code=429)\n"
    )

    assert NUMERO not in refus_temporaires(muet, "t")[0][1]
    assert NUMERO in refus_temporaires(parlant, "t")[0][1]


def test_chaque_refus_temporaire_porte_le_numero():
    muets = [ou for ou, texte in _tous_les_refus() if NUMERO not in texte]

    assert muets == [], (
        "ces refus 429 repartent sans le numéro. Un refus temporaire arrive AVANT la "
        "route, donc avant le garde de crise : c'est la seule réponse du produit où "
        f"personne ne rattrape la détresse — {muets}"
    )


def test_le_refus_d_ECRITURE_porte_le_numero_sur_une_vraie_route():
    """La mesure, pas la lecture : `/journal` n'est pas gardé, et son garde de crise ne
    s'exécute jamais quand le middleware a déjà refusé."""
    client = TestClient(app)
    entree = {"title": "ce soir", "content": "je vide mon sac"}

    for _ in range(limite.PAR_MINUTE_ECRITURE):
        assert client.post("/journal", json=entree).status_code == 200

    trop = client.post("/journal", json=entree)

    assert trop.status_code == 429
    assert NUMERO in str(trop.json()), trop.json()


def test_les_cgu_promettent_bien_ce_refus_la():
    """Le lien : la phrase lue par le client et la règle appliquée doivent vivre ou
    mourir ensemble."""
    cgu = (STATIC / "cgu.html").read_text(encoding="utf-8-sig")

    assert "Un refus temporaire renvoie toujours" in cgu
