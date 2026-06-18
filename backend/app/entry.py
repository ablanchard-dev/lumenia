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

Le parcours filtre sans exclure : chaque épreuve peut être passée après
2 échecs, et terminer le parcours ouvre toujours l'accès.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import List, Optional, Set

from .chat import _normalize
from .llm import _chat

# kind (porté par CHAQUE item) :
#   "qcm"       = QCM à 4 choix (A/B/C/D) — la clé est la lettre attendue
#   "objective" = réponse attendue (tolérance + juge LLM en seconde lecture)
#   "open"      = pas de mauvaise réponse — matière à profilage uniquement
_BANK_PATH = Path(__file__).with_name("entry_bank.json")
PARCOURS: List[dict] = json.loads(_BANK_PATH.read_text(encoding="utf-8"))

_BY_ID = {item["id"]: {**item, "dimension": step["dimension"]}
          for step in PARCOURS for item in step["pool"]}


# Nombre d'épreuves tirées par dimension (~27 au total, esprit WAIS). PROVISOIRE :
# la longueur définitive du parcours ET le seuil de réussite relèvent du protocole
# de Blandine (psychologue). Plafonné à la taille du pool pour éviter tout débordement.
_DRAW_PER_DIM = {
    "verbale": 5,
    "fluide": 5,
    "memoire": 5,
    "spatial": 5,
    "vitesse": 5,
    "libre": 2,
}
_DRAW_DEFAULT = 5


def get_parcours(exclude: Optional[Set[str]] = None) -> dict:
    """Tire ~30 épreuves (réparties par dimension), en évitant si possible les
    ids déjà vus, et en complétant depuis le pool si la réserve de non-vus est
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
    valide pas « 33 ») ; réponse textuelle → inclusion en forme compacte."""
    acc_norm = _normalize(accepted).strip()
    if _NUM_RE.fullmatch(acc_norm):
        target = float(acc_norm.replace(",", "."))
        return any(abs(n - target) < 1e-9 for n in _numbers(answer))
    acc_compact = re.sub(r"[^a-z0-9]", "", acc_norm)
    norm_compact = re.sub(r"[^a-z0-9]", "", _normalize(answer))
    return bool(acc_compact) and acc_compact in norm_compact


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
    if verdict and "OUI" in verdict.upper():
        return {"ok": True}
    return {"ok": False, "hint": c["hint"]}


def entry_summary(results: List[dict]) -> dict:
    """Condense les résultats du parcours pour le profil cognitif (KV profile.entry)."""
    strengths = [r["dimension"] for r in results
                 if r.get("ok") and not r.get("skipped") and r["dimension"] != "libre"]
    creative = next((r.get("answer", "").strip() for r in results
                     if r["dimension"] == "libre" and r.get("answer", "").strip()), "")
    return {"strengths": strengths, "creative": creative[:200]}
