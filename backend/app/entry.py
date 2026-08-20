# -*- coding: utf-8 -*-
"""Portail d'entrée de Lumenia : mini-parcours de défis cognitifs.

Cahier des charges (§3.1) : l'entrée se fait par un MINI-PARCOURS d'épreuves
— pensée latérale, logique, raisonnement, similitudes, expression libre —
et non par une énigme unique. Double fonction :
  1. seuil symbolique en résonance avec les schémas de pensée atypiques ;
  2. initialisation du profilage cognitif (§3.3) : les réponses alimentent
     le profil injecté ensuite dans les prompts du chat.

La banque de questions vit dans `entry_bank.json` (même dossier) pour être
enrichie sans toucher au code — y compris par des non-développeurs (items
inspirés de l'esprit WAIS/CRT, mais ORIGINAUX : ne jamais copier d'items de
tests psychométriques réels, protégés et éthiquement réservés au cabinet).

Le parcours est ÉLIMINATOIRE (protocole clinique de Blandine) : il faut
>= ENTRY_PASS_RATIO (0.85) des 30 questions notées, soit 26/30 — 4 erreurs
maximum. Une épreuve peut être passée après 2 échecs, mais `main.py` compte
`score = ok and not skipped` sur `total = len(results)` : **passer une épreuve
équivaut donc à la rater**. Terminer le parcours n'ouvre PAS l'accès en soi.

⚠️ Point de fragilité connu (mesuré le 15/08) : un tirage contient en moyenne
14,65 épreuves `objective` (réponse libre) sur 30. Elles sont d'abord validées
par correspondance sur la liste de synonymes de l'item ; si la formulation du
candidat n'y figure pas, la décision revient au juge LLM — et `_chat` renvoie
None quand aucune clé n'est configurée ou que le quota gratuit est épuisé
(Gemini : 20 req/jour), ce qui compte la réponse comme FAUSSE. Sans juge LLM
disponible, le seuil devient nettement plus dur que prévu par le protocole.
"""
from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import List, Optional, Set

from .chat import _normalize
from .llm import _chat

log = logging.getLogger(__name__)

# kind (porté par CHAQUE item) :
#   "qcm"       = QCM à 4 choix (A/B/C/D) — la clé est la lettre attendue
#   "objective" = réponse attendue (tolérance + juge LLM en seconde lecture)
#   "open"      = pas de mauvaise réponse — matière à profilage uniquement
_BANK_PATH = Path(__file__).with_name("entry_bank.json")
PARCOURS: List[dict] = json.loads(_BANK_PATH.read_text(encoding="utf-8"))

_BY_ID = {item["id"]: {**item, "dimension": step["dimension"]}
          for step in PARCOURS for item in step["pool"]}


# Seuil de réussite du parcours d'entrée. Source de vérité SERVEUR (le front a sa
# propre constante ENTRY_PASS_RATIO ; les deux doivent rester alignées).
ENTRY_PASS_RATIO = 0.85

def entry_passed(score: int, total: int) -> bool:
    """Vrai si le parcours d'entrée est validé (>= 85% des questions notées)."""
    return total > 0 and (score / total) >= ENTRY_PASS_RATIO


def entry_is_gradable(results) -> bool:
    """Vrai si le parcours a pu être CORRIGÉ en entier.

    `verify_challenge` distingue déjà « réponse fausse » de « juge injoignable »
    (`undetermined`). Sans cette fonction ce drapeau s'arrêtait au front : le serveur
    ne voyait qu'un `ok=False` de plus et prononçait un échec. Or un tirage contient
    en moyenne 14,65 épreuves à réponse libre sur 30, pour 4 erreurs autorisées : une
    panne de juge rendait le parcours quasi impassable **en annonçant à la personne
    qu'elle avait échoué un test cognitif**.

    On ne retire PAS ces items du dénominateur — ce serait rouvrir la faille du
    dénominateur piloté par le client. On refuse de rendre un verdict, ce qui est
    exactement ce que `undetermined` veut dire.
    """
    return not any(r.get("undetermined") for r in results)


def entry_is_complete(n_results: int) -> bool:
    """Vrai si le parcours rendu a bien la longueur du parcours tiré.

    Le seuil est un RATIO : sans cette vérification, le dénominateur vient du client.
    Un appel direct envoyant un seul item juste obtenait 1/1 = 100 % et ouvrait le
    chat — le gate était bien côté serveur, mais il faisait confiance au client sur
    le nombre d'épreuves. Vérifié en l'exécutant le 15/08.

    La longueur attendue est DÉRIVÉE de `_DRAW_PER_DIM` (voir `entry_scored_length`),
    jamais réécrite à la main : changer le protocole ne doit pas laisser ce garde-fou
    en arrière.
    """
    return n_results == entry_scored_length()

# Nombre d'épreuves tirées par dimension. Total = 30 questions NOTÉES (6 par
# dimension cognitive), dans l'esprit d'un test WAIS adulte éliminatoire.
# Longueur (30) et seuil de réussite (0.85 = ENTRY_PASS_RATIO)
# confirmés par le protocole clinique de Blandine (psychologue). Plafonné à la
# taille du pool pour éviter tout débordement.
#
# `libre` (expression libre, kind=open) est à 0 : ces items n'ont pas de bonne
# réponse, ils ne peuvent donc pas compter dans un score éliminatoire (le front les
# exclut déjà du dénominateur). Pour réintroduire une étape de profilage §3.3 en fin
# de parcours (non notée, clôture douce), il suffit de remettre "libre": 1 ou 2 ici.
_DRAW_PER_DIM = {
    "verbale": 6,
    "fluide": 6,
    "memoire": 6,
    "spatial": 6,
    "vitesse": 6,
    "libre": 0,
}
_DRAW_DEFAULT = 6


def entry_scored_length() -> int:
    """Nombre d'épreuves NOTÉES réellement tirées par `get_parcours`.

    Reprend le MÊME plafonnement par pool que le tirage : dériver la longueur au lieu
    de réécrire « 30 » évite que le garde-fou et le tirage divergent le jour où un pool
    rétrécit ou qu'une dimension change.
    """
    return sum(min(_DRAW_PER_DIM.get(s["dimension"], _DRAW_DEFAULT), len(s["pool"]))
               for s in PARCOURS)


def get_parcours(exclude: Optional[Set[str]] = None) -> dict:
    """Tire 30 épreuves notées (6 par dimension cognitive), en évitant si possible
    les ids déjà vus, et en complétant depuis le pool si la réserve de non-vus est
    insuffisante."""
    exclude = exclude or set()
    steps = []
    for step in PARCOURS:
        pool = step["pool"]
        n = min(_DRAW_PER_DIM.get(step["dimension"], _DRAW_DEFAULT), len(pool))
        fresh = [i for i in pool if i["id"] not in exclude]
        if len(fresh) >= n:
            chosen = random.sample(fresh, n)
        else:  # plus assez de non-vus → on complète depuis le reste du pool
            rest = [i for i in pool if i not in fresh]
            chosen = fresh + random.sample(rest, min(n - len(fresh), len(rest)))
        for item in chosen:
            entry = {
                "id": item["id"],
                "dimension": step["dimension"],
                "label": step["label"],
                "kind": item["kind"],
                "question": item["question"],
            }
            if item.get("consigne"):
                entry["consigne"] = item["consigne"]
            if item["kind"] == "qcm":
                entry["choices"] = item["choices"]
            if item.get("temps_sec"):
                entry["temps_sec"] = item["temps_sec"]
            steps.append(entry)
    return {"steps": steps, "total": len(steps)}


def get_challenge() -> dict:
    """Compat v2.2 : une seule épreuve objective, au hasard."""
    objectives = [i for i in _BY_ID.values() if i["kind"] == "objective"]
    c = random.choice(objectives)
    return {"id": c["id"], "question": c["question"]}


_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> List[float]:
    return [float(n.replace(",", ".")) for n in _NUM_RE.findall(text)]


def _matches(accepted: str, answer: str) -> bool:
    """Réponse numérique → égalité exacte sur les nombres extraits (« 133 » ne
    valide pas « 33 ») ; réponse textuelle → inclusion en forme compacte ;
    réponse purement symbolique (ex. chiffrement « #%&@ ») → comparaison en
    ignorant seulement les espaces (la compaction alphanumérique la viderait)."""
    acc_norm = _normalize(accepted).strip()
    if _NUM_RE.fullmatch(acc_norm):
        target = float(acc_norm.replace(",", "."))
        return any(abs(n - target) < 1e-9 for n in _numbers(answer))
    acc_compact = re.sub(r"[^a-z0-9]", "", acc_norm)
    norm_compact = re.sub(r"[^a-z0-9]", "", _normalize(answer))
    if acc_compact:
        return acc_compact in norm_compact
    acc_sym = re.sub(r"\s+", "", acc_norm)
    ans_sym = re.sub(r"\s+", "", _normalize(answer))
    return bool(acc_sym) and acc_sym in ans_sym


def verify_challenge(challenge_id: str, answer: str) -> dict:
    c = _BY_ID.get(challenge_id)
    if not c:
        return {"ok": False, "error": "unknown_challenge"}

    # QCM : la réponse est une lettre (A/B/C/D), comparée à la clé. Pas de LLM.
    # On tolère aussi le texte exact du bon choix (robustesse côté client).
    if c["kind"] == "qcm":
        key = str(c.get("answer", "")).strip().upper()
        picked = str(answer).strip()
        correct_text = str((c.get("choices") or {}).get(key, "")).strip()
        ok = picked.upper() == key or (correct_text and _normalize(picked) == _normalize(correct_text))
        return {"ok": True} if ok else {"ok": False, "hint": c.get("explication", "")}

    # Épreuve ouverte : pas de mauvaise réponse, juste de la matière à profil.
    if c["kind"] == "open":
        if len(answer.strip()) >= 2:
            return {"ok": True}
        return {"ok": False, "hint": "Il n'y a pas de bonne réponse ici — écris ce qui te vient."}

    if any(_matches(accepted, answer) for accepted in c["answers"]):
        return {"ok": True}

    # Réponse non reconnue : le LLM juge avec tolérance (synonymes, formulations).
    verdict = _chat(
        f"""Énigme : « {c['question']} »
Réponses attendues : {", ".join(c['answers'])}
Réponse du candidat : « {answer} »

Cette réponse est-elle équivalente ou raisonnablement valable ? Réponds par un seul mot : OUI ou NON.""",
        temperature=0.0,
        max_tokens=500,
    )
    if verdict is None:
        # Le juge n'a PAS répondu (aucune clé, quota épuisé, toute la chaîne HS).
        # On ne sait pas si la réponse est bonne — et « je ne sais pas » n'est pas
        # « c'est faux ». On garde ok=False pour ne pas offrir le point, mais on
        # marque l'épreuve comme NON JUGÉE : sans ce drapeau, une panne de juge
        # produit un verdict négatif indiscernable d'une vraie erreur, et fait
        # échouer un candidat valable sans que personne ne le voie.
        # ⚠️ Le seuil (0.85) et la longueur (30) sont un protocole verrouillé :
        # décider si ces épreuves sortent du dénominateur est un choix produit
        # (Alex + Blandine), pas un correctif. Ici on rend seulement le fait visible.
        log.warning("Juge LLM indisponible sur l'épreuve %s — épreuve NON JUGÉE.", c.get("id"))
        return {"ok": False, "undetermined": True, "hint": c["hint"]}
    if "OUI" in verdict.upper():
        return {"ok": True}
    return {"ok": False, "hint": c["hint"]}


def entry_summary(results: List[dict]) -> dict:
    """Condense les résultats du parcours pour le profil cognitif (KV profile.entry)."""
    strengths = [r["dimension"] for r in results
                 if r.get("ok") and not r.get("skipped") and r["dimension"] != "libre"]
    creative = next((r.get("answer", "").strip() for r in results
                     if r["dimension"] == "libre" and r.get("answer", "").strip()), "")
    return {"strengths": strengths, "creative": creative[:200]}
