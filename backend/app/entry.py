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

# kind: "objective" = réponse attendue (tolérance + juge LLM en seconde lecture)
#       "open"      = pas de mauvaise réponse — matière à profilage uniquement
_BANK_PATH = Path(__file__).with_name("entry_bank.json")
PARCOURS: List[dict] = json.loads(_BANK_PATH.read_text(encoding="utf-8"))

_BY_ID = {item["id"]: {**item, "dimension": step["dimension"], "kind": step["kind"]}
          for step in PARCOURS for item in step["pool"]}


# Épreuves tirées par dimension : 2 pour les dimensions objectives (parcours
# plus étoffé, esprit WAIS), 1 pour l'expression libre (open). → 9 au total.
_PER_DIM_DEFAULT = 2
_PER_DIM_BY_KIND = {"open": 1}


def get_parcours(exclude: Optional[Set[str]] = None) -> dict:
    """Tire plusieurs épreuves par dimension (2 objectives, 1 ouverte), en
    évitant si possible les ids déjà vus."""
    exclude = exclude or set()
    steps = []
    for step in PARCOURS:
        n = _PER_DIM_BY_KIND.get(step["kind"], _PER_DIM_DEFAULT)
        pool = step["pool"]
        fresh = [i for i in pool if i["id"] not in exclude]
        if len(fresh) >= n:
            chosen = random.sample(fresh, n)
        else:  # plus assez de non-vus → on complète depuis le reste du pool
            rest = [i for i in pool if i not in fresh]
            chosen = fresh + random.sample(rest, min(n - len(fresh), len(rest)))
        for item in chosen:
            steps.append({
                "id": item["id"],
                "dimension": step["dimension"],
                "label": step["label"],
                "kind": step["kind"],
                "question": item["question"],
            })
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
                 if r.get("ok") and not r.get("skipped") and r["dimension"] != "creative"]
    creative = next((r.get("answer", "").strip() for r in results
                     if r["dimension"] == "creative" and r.get("answer", "").strip()), "")
    return {"strengths": strengths, "creative": creative[:200]}
