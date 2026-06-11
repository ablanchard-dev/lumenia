# -*- coding: utf-8 -*-
"""Cœur conversationnel de Lumenia : chat LLM, analyse interne des signaux,
portail d'entrée par défi cognitif.

L'évaluation se fait EN INTERNE : on n'affiche jamais de questionnaire à
l'utilisateur. Chaque message est analysé côté serveur (signaux de détresse)
et le flag de risque pilote la bannière 3114 côté UI.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from .llm import SYSTEM_PROMPT, _client, complete

import logging

log = logging.getLogger("lumenia.chat")


# ----------------------------------------------------------------------------
# Analyse interne des signaux (remplace l'auto-évaluation visible)
# ----------------------------------------------------------------------------

# Lexique de détresse aiguë (FR + EN), comparé en version normalisée (minuscules,
# sans accents). Restreint aux signaux forts pour éviter les faux positifs
# anxiogènes — mais il doit couvrir les paraphrases courantes (moyens, fatigue
# de vivre), pas seulement le mot « suicide ».
_CRISIS_PATTERNS = [
    # intention directe
    r"suicid",                        # suicide, suicidaire (préfixe, pas de \b : "antisuicide" est théorique)
    r"\bme tuer\b",
    r"\ben finir\b",
    r"\bmettre fin a (?:mes jours|ma vie)\b",
    r"\bme foutre en l'?air\b",
    # fatigue de vivre
    r"\bplus envie de vivre\b",
    r"\benvie de mourir\b",
    r"\b(?:je )?veux mourir\b",
    r"\b(?:je )?veux crever\b",
    r"\bplus la force de (?:continuer|vivre|me battre)\b",
    r"\barrete pour toujours\b",      # « que ça s'arrête pour toujours »
    r"\bplus (?:jamais )?me reveiller\b",
    r"\bdisparaitre pour de bon\b",
    r"\bidees noires\b",
    # moyens évoqués
    r"\bme pendre\b",
    r"\bme noyer\b",
    r"\bme jeter (?:sous|du haut|dans le vide|par la fenetre)\b",
    r"\bsauter (?:du pont|d'un pont|par la fenetre|de la fenetre|dans le vide|du toit)\b",
    r"\bavale\w*\b.{0,16}\btoute?s?\b.{0,16}\b(?:pilules|cachets|medicaments|comprimes)\b",
    # auto-mutilation
    r"\bme faire du mal\b",
    r"\bme blesser\b",
    r"\bme tailler les veines\b",
    r"\bme mutiler\b",
    r"\bscarifi",
    # anglais
    r"\bkill myself\b",
    r"\bwant to die\b",
    r"\bwanna die\b",
    r"\bend my life\b",
    r"\bend it all\b",
    r"\bbetter off dead\b",
    r"\bhurt myself\b",
    r"\bself ?harm\b",
]

# Formes compactes (sans espaces ni ponctuation) : attrape « sui cide », « s u i c i d e »…
_CRISIS_COMPACT = ["suicid", "killmyself", "wanttodie", "endmylife", "veuxmourir", "veuxcrever"]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def detect_crisis(message: str) -> bool:
    norm = _normalize(message)
    if any(re.search(p, norm) for p in _CRISIS_PATTERNS):
        return True
    compact = re.sub(r"[^a-z0-9]", "", norm)
    return any(s in compact for s in _CRISIS_COMPACT)


SAFETY_REPLY = (
    "Ce que tu viens d'écrire compte, et je le prends au sérieux.\n\n"
    "Je suis un outil, pas un humain — et là, tu mérites une vraie présence. "
    "Le 3114 est le numéro national de prévention du suicide : gratuit, 24h/24, "
    "tenu par des professionnels formés. Tu peux appeler maintenant, même sans savoir quoi dire.\n\n"
    "- **3114** — écoute et soutien, 24h/24, 7j/7\n"
    "- **15** — urgence médicale (SAMU)\n"
    "- **112** — urgence européenne\n\n"
    "Je reste là si tu veux continuer à écrire. Rien de ce que tu dis ici n'est « trop »."
)


# ----------------------------------------------------------------------------
# Chat conversationnel
# ----------------------------------------------------------------------------

FALLBACK_REPLY = (
    "Je n'arrive pas à joindre mon moteur d'intelligence pour le moment. "
    "Réessaie dans une minute — en attendant, si tu étais venu·e débloquer une tâche, "
    "écris simplement la toute première action de moins de 5 minutes, et fais-la."
)

_MAX_HISTORY = 20


_DIMENSION_LABELS = {
    "laterale": "pensée latérale",
    "logique": "logique",
    "abstraite": "associations abstraites",
}


def _profile_directives(low_stim: bool, pacing: str, entry_profile: Optional[dict] = None) -> str:
    parts = []
    if low_stim:
        parts.append(
            "- Profil low-stim actif : réponses encore plus courtes (5 lignes max), "
            "pas de listes longues, pas d'emphase superflue."
        )
    if pacing == "slow":
        parts.append(
            "- Rythme lent demandé : une seule idée ou action par réponse, "
            "jamais plusieurs pistes en parallèle."
        )
    elif pacing == "fast":
        parts.append("- Rythme rapide accepté : tu peux être plus dense, rester structuré.")
    if entry_profile:
        strengths = [_DIMENSION_LABELS.get(d, d) for d in entry_profile.get("strengths") or []]
        if strengths:
            parts.append(
                f"- Parcours d'entrée : à l'aise en {', '.join(strengths)} — "
                "tu peux t'appuyer sur ces registres (analogies, structure logique)."
            )
        creative = (entry_profile.get("creative") or "").strip()
        if creative:
            parts.append(
                f"- Sa réponse libre au parcours d'entrée : « {creative} ». "
                "Indice sur son style cognitif ; n'y fais référence que si c'est pertinent."
            )
    return ("\nAdaptations au profil de l'utilisateur :\n" + "\n".join(parts)) if parts else ""


def chat_reply(
    message: str,
    history: Optional[List[dict]] = None,
    low_stim: bool = False,
    pacing: str = "normal",
    entry_profile: Optional[dict] = None,
) -> dict:
    """Réponse conversationnelle. Retourne {reply, risk}.

    L'analyse de risque est faite ici, en interne, sur le message utilisateur.
    """
    risk = detect_crisis(message)
    if risk:
        return {"reply": SAFETY_REPLY, "risk": True}

    if _client is None:
        return {"reply": FALLBACK_REPLY, "risk": False}

    messages = [{"role": "system", "content": SYSTEM_PROMPT + _profile_directives(low_stim, pacing, entry_profile)}]
    for turn in (history or [])[-_MAX_HISTORY:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    reply = complete(messages, temperature=0.6, max_tokens=3000)
    return {"reply": reply or FALLBACK_REPLY, "risk": False}


# Le portail d'entrée (mini-parcours de défis cognitifs) vit dans entry.py.
