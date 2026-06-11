# -*- coding: utf-8 -*-
"""Portail d'entrée de Lumenia : mini-parcours de défis cognitifs.

Cahier des charges (§3.1) : l'entrée se fait par un MINI-PARCOURS d'épreuves
— pensée latérale, micro-épreuve logique, association abstraite, expression
libre — et non par une énigme unique. Double fonction :
  1. seuil symbolique en résonance avec les schémas de pensée atypiques ;
  2. initialisation du profilage cognitif (§3.3) : les réponses alimentent
     le profil injecté ensuite dans les prompts du chat.

Le parcours filtre sans exclure : chaque épreuve peut être passée après
3 tentatives, et terminer le parcours ouvre toujours l'accès.
"""
from __future__ import annotations

import random
import re
from typing import List, Optional

from .chat import _normalize
from .llm import _chat

# Une épreuve par dimension, tirée au hasard dans un pool. kind:
#   "objective" : réponse attendue (tolérance + juge LLM en seconde lecture)
#   "open"      : pas de mauvaise réponse — matière à profilage uniquement
PARCOURS = [
    {
        "dimension": "laterale",
        "label": "Pensée latérale",
        "kind": "objective",
        "pool": [
            {
                "id": "echo",
                "question": "Je parle toutes les langues du monde sans en avoir appris aucune. Qui suis-je ?",
                "hint": "On m'entend surtout en montagne.",
                "answers": ["echo", "l'echo", "un echo"],
            },
            {
                "id": "trou",
                "question": "Plus on m'enlève de matière, plus je grandis. Qui suis-je ?",
                "hint": "Pense à une pelle.",
                "answers": ["trou", "le trou", "un trou"],
            },
            {
                "id": "prenom",
                "question": "C'est à toi, mais les autres l'utilisent bien plus souvent que toi. Qu'est-ce que c'est ?",
                "hint": "On te le demande quand on te rencontre.",
                "answers": ["prenom", "nom", "mon prenom", "mon nom", "le prenom", "le nom"],
            },
            {
                "id": "silence",
                "question": "Dès qu'on prononce mon nom, je disparais. Qui suis-je ?",
                "hint": "Il règne dans une bibliothèque.",
                "answers": ["silence", "le silence"],
            },
            {
                "id": "aujourdhui",
                "question": "Je suis l'avenir d'hier et le passé de demain. Qui suis-je ?",
                "hint": "Tu es en plein dedans.",
                "answers": ["aujourd'hui", "aujourdhui", "le present", "present"],
            },
        ],
    },
    {
        "dimension": "logique",
        "label": "Micro-logique",
        "kind": "objective",
        "pool": [
            {
                "id": "suite",
                "question": "Complète la suite : 2, 3, 5, 9, 17, … ?",
                "hint": "Regarde comment on passe d'un nombre au suivant : ×2, puis…",
                "answers": ["33"],
            },
            {
                "id": "suite_pas",
                "question": "Complète la suite : 3, 4, 6, 9, 13, … ?",
                "hint": "Regarde ce qu'on ajoute à chaque pas : +1, +2, +3…",
                "answers": ["18"],
            },
            {
                "id": "zorg",
                "question": "Tous les Zorgs sont bleus. Certains êtres bleus chantent. "
                            "Peut-on être certain qu'au moins un Zorg chante ? (oui / non)",
                "hint": "Les chanteurs sont bleus… mais qui te dit que ce sont des Zorgs ?",
                "answers": ["non"],
            },
        ],
    },
    {
        "dimension": "abstraite",
        "label": "Association abstraite",
        "kind": "objective",
        "pool": [
            {
                "id": "horloge_coeur",
                "question": "Quel point commun vois-tu entre une horloge et un cœur ?",
                "hint": "Écoute-les.",
                "answers": ["bat", "battent", "battement", "rythme", "tic", "pulsation", "temps"],
            },
            {
                "id": "graine_idee",
                "question": "Quel point commun vois-tu entre une graine et une idée ?",
                "hint": "Que deviennent-elles quand on s'en occupe ?",
                "answers": ["germe", "germent", "pousse", "poussent", "grandit", "grandissent",
                            "planter", "semer", "cultiver", "fleurir", "murir"],
            },
            {
                "id": "brouillard_oubli",
                "question": "Quel point commun vois-tu entre le brouillard et l'oubli ?",
                "hint": "Que font-ils aux contours des choses ?",
                "answers": ["estompe", "efface", "flou", "floute", "masque", "cache", "voile",
                            "disparait", "disparaitre", "brouille"],
            },
        ],
    },
    {
        "dimension": "creative",
        "label": "Expression libre",
        "kind": "open",
        "pool": [
            {
                "id": "penser_comme",
                "question": "Complète à ta façon : « Penser, pour moi, c'est comme… »",
            },
            {
                "id": "cerveau_lieu",
                "question": "Si ton esprit était un lieu, lequel serait-il ? Décris-le en une phrase.",
            },
            {
                "id": "mot_invente",
                "question": "Invente un mot qui n'existe pas, et donne sa définition.",
            },
        ],
    },
]

_BY_ID = {item["id"]: {**item, "dimension": step["dimension"], "kind": step["kind"]}
          for step in PARCOURS for item in step["pool"]}


def get_parcours() -> dict:
    """Tire une épreuve par dimension, dans l'ordre du parcours."""
    steps = []
    for step in PARCOURS:
        item = random.choice(step["pool"])
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


def verify_challenge(challenge_id: str, answer: str) -> dict:
    c = _BY_ID.get(challenge_id)
    if not c:
        return {"ok": False, "error": "unknown_challenge"}

    # Épreuve ouverte : pas de mauvaise réponse, juste de la matière à profil.
    if c["kind"] == "open":
        if len(answer.strip()) >= 2:
            return {"ok": True}
        return {"ok": False, "hint": "Il n'y a pas de bonne réponse ici — écris ce qui te vient."}

    norm = _normalize(answer).strip()
    norm_compact = re.sub(r"[^a-z0-9]", "", norm)
    for accepted in c["answers"]:
        acc_compact = re.sub(r"[^a-z0-9]", "", _normalize(accepted))
        if acc_compact and acc_compact in norm_compact:
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
