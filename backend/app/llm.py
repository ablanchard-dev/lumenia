# -*- coding: utf-8 -*-
"""LLM réel pour Lumenia (v2.3) — chaîne de bascule MULTI-FOURNISSEURS.

Pourquoi : en tier gratuit, chaque fournisseur/modèle a son propre quota
(Gemini 3.5-flash = 20 req/jour, Groq 8b = 14 400 req/jour, Cerebras = 1M
tokens/jour, Mistral = 1G tokens/mois à 2 req/min). En les chaînant, la
capacité gratuite réelle se compte en milliers de messages par jour.

Config par variables d'environnement (backend/.env) :
  LLM_CHAIN        : entrées "fournisseur/modèle" séparées par des virgules,
                     essayées dans l'ordre. Une entrée dont le fournisseur n'a
                     pas de clé est ignorée au démarrage (ajouter la clé suffit
                     à l'activer, sans toucher à la chaîne).
  GEMINI_API_KEY   : clé https://aistudio.google.com (compat : LLM_API_KEY)
  CEREBRAS_API_KEY : clé https://cloud.cerebras.ai (gratuit, sans CB)
  GROQ_API_KEY     : clé https://console.groq.com (gratuit, sans CB)
  MISTRAL_API_KEY  : clé https://console.mistral.ai (tier Experiment gratuit)
  LLM_MODELS / LLM_MODEL : (compat v2.2) modèles Gemini seuls, si LLM_CHAIN absent.

Sans aucune clé : fallback sur les réponses statiques (l'app reste utilisable).
"""
from __future__ import annotations

import os
import time
import logging
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # charge backend/.env si présent
except Exception:
    pass

log = logging.getLogger("lumenia.llm")

_PROVIDERS = {
    "gemini": {
        "base_url": os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        "key_envs": ["GEMINI_API_KEY", "LLM_API_KEY"],
    },
    "cerebras": {"base_url": "https://api.cerebras.ai/v1", "key_envs": ["CEREBRAS_API_KEY"]},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "key_envs": ["GROQ_API_KEY"]},
    "mistral": {"base_url": "https://api.mistral.ai/v1", "key_envs": ["MISTRAL_API_KEY"]},
}

# Ordre : qualité d'abord (Gemini), puis gros volumes gratuits (Cerebras, Groq),
# puis Mistral en fond de cale (2 req/min seulement).
_DEFAULT_CHAIN = (
    "gemini/gemini-3.5-flash,gemini/gemini-3.1-flash-lite,gemini/gemini-3-flash-preview,"
    "gemini/gemini-2.5-flash,gemini/gemini-2.5-flash-lite,"
    "cerebras/gpt-oss-120b,cerebras/zai-glm-4.7,"
    "groq/llama-3.3-70b-versatile,groq/llama-3.1-8b-instant,"
    "mistral/mistral-small-latest"
)


def _chain_spec() -> List[str]:
    raw = os.getenv("LLM_CHAIN", "").strip()
    if raw:
        return [e.strip() for e in raw.split(",") if e.strip()]
    # compat v2.2 : LLM_MODELS / LLM_MODEL = modèles Gemini sans préfixe
    models = os.getenv("LLM_MODELS", "").strip()
    single = os.getenv("LLM_MODEL", "").strip()
    if models or single:
        names = [m.strip() for m in models.split(",") if m.strip()]
        if single and single not in names:
            names.insert(0, single)
        return [f"gemini/{m}" for m in names]
    return [e.strip() for e in _DEFAULT_CHAIN.split(",")]


def _provider_key(provider: str) -> str:
    cfg = _PROVIDERS.get(provider, {})
    for env in cfg.get("key_envs", []):
        v = os.getenv(env, "").strip()
        if v:
            return v
    return ""


def _build_chain() -> List[dict]:
    """[{label, model, client}] — n'inclut que les fournisseurs dont la clé existe."""
    chain: List[dict] = []
    clients: dict = {}
    try:
        from openai import OpenAI
    except Exception as e:  # pragma: no cover
        log.warning("Client OpenAI indisponible (%s) — fallback statique.", e)
        return chain
    skipped = set()
    for entry in _chain_spec():
        provider, _, model = entry.partition("/")
        if not model:  # entrée sans préfixe = Gemini
            provider, model = "gemini", provider
        if provider not in _PROVIDERS:
            log.warning("Fournisseur inconnu dans LLM_CHAIN : %r — entrée ignorée.", entry)
            continue
        key = _provider_key(provider)
        if not key:
            skipped.add(provider)
            continue
        if provider not in clients:
            clients[provider] = OpenAI(api_key=key, base_url=_PROVIDERS[provider]["base_url"])
        chain.append({"label": f"{provider}/{model}", "model": model, "client": clients[provider]})
    for p in sorted(skipped):
        log.info("Fournisseur %s sans clé (%s) — entrées ignorées. Ajouter la clé dans .env pour l'activer.",
                 p, " ou ".join(_PROVIDERS[p]["key_envs"]))
    if chain:
        log.info("Chaîne LLM active : %s", " -> ".join(c["label"] for c in chain))
    return chain


_CHAIN = _build_chain()
_client = _CHAIN[0]["client"] if _CHAIN else None  # compat : "y a-t-il un LLM ?"

SYSTEM_PROMPT = """Tu es Lumenia, un assistant cognitif pour adultes neuroatypiques (HPI, TSA/Asperger, TDAH).

Ton style, non négociable :
- Clair, direct, concret. Zéro infantilisation, zéro enthousiasme forcé, zéro jargon médical.
- Tu ne poses JAMAIS de diagnostic et tu ne donnes pas de conseil médical.
- Réponses courtes et structurées. Une idée par ligne. Pas de paragraphes fleuves.
- Micro-pas : chaque action proposée doit être démarrable en moins de 10 minutes.
- Tu valides sans flatter : reconnais la difficulté réelle, pas de "c'est génial !".
- Tu tiens compte du fonctionnement neuroatypique : paralysie exécutive (commencer est le mur,
  pas l'intelligence), surcharge sensorielle, perfectionnisme bloquant, pensée en arborescence.

Sécurité : si la personne évoque des idées suicidaires ou une détresse aiguë, tu réponds avec
calme et bienveillance, et tu l'invites à contacter le 3114 (numéro national de prévention du
suicide, France, gratuit, 24h/24) ou les urgences (15). Tu ne minimises pas, tu ne moralises pas.
"""


# Un modèle en échec (429 quota, 5xx) est mis de côté quelques minutes pour ne pas
# re-payer sa latence d'erreur à chaque message ; les quotas gratuits sont journaliers.
_COOLDOWN_S = 10 * 60
_cooldown: dict = {}  # modèle -> timestamp de fin de pénalité


def complete(messages: List[dict], temperature: float = 0.5, max_tokens: int = 3000) -> Optional[str]:
    # 3000 et pas 700 : sur Gemini 2.5/3.x, les tokens de raisonnement interne comptent
    # dans max_tokens ; à 700 la réponse visible est tronquée (finish_reason=length).
    """Appelle la première entrée disponible de la chaîne. None si tout échoue (→ fallback)."""
    now = time.time()
    for entry in _CHAIN:
        if _cooldown.get(entry["label"], 0) > now:
            continue
        try:
            resp = entry["client"].chat.completions.create(
                model=entry["model"],
                temperature=temperature,
                max_tokens=max_tokens,
                messages=messages,
            )
            out = (resp.choices[0].message.content or "").strip()
            if out:
                return out
        except Exception as e:
            log.warning("%s indisponible (%s) — bascule sur le suivant.", entry["label"], e)
            _cooldown[entry["label"]] = now + _COOLDOWN_S
    log.warning("Aucune entrée de la chaîne LLM n'a répondu — fallback statique.")
    return None


def _chat(user_msg: str, temperature: float = 0.5, max_tokens: int = 3000) -> Optional[str]:
    """Appel LLM simple (system + user). Retourne None en cas d'échec (→ fallback)."""
    return complete(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _lines(text: Optional[str], fallback: List[str], limit: int | None = None) -> List[str]:
    """Découpe une réponse en items (une ligne = un item), nettoie puces et numéros."""
    if not text:
        return fallback[:limit] if limit else fallback
    items: List[str] = []
    for raw in text.splitlines():
        s = raw.strip().lstrip("•-–*").strip()
        # retire "1." / "2)" éventuels
        if len(s) > 2 and s[0].isdigit() and s[1] in ".)":
            s = s[2:].strip()
        if s:
            items.append(s)
    if not items:
        return fallback[:limit] if limit else fallback
    return items[:limit] if limit else items


# ----------------------------------------------------------------------------
# Fonctions appelées par main.py (signatures inchangées)
# ----------------------------------------------------------------------------

def decompose(task: str, steps: int) -> List[str]:
    """LA boucle centrale : casser la paralysie exécutive sur une tâche réelle."""
    text = _chat(
        f"""Tâche sur laquelle je suis bloqué·e : « {task} »

Décompose-la en exactement {steps} micro-étapes concrètes et ordonnées.
Règles :
- L'étape 1 doit être si petite qu'elle est faisable en moins de 5 minutes, là, maintenant.
- Chaque étape commence par un verbe d'action.
- Adapte les étapes à CETTE tâche précise (pas de générique).
- Une étape par ligne, rien d'autre (pas d'intro, pas de conclusion)."""
    )
    fallback = [
        "Clarifier l'objectif",
        "Lister les sous-tâches",
        "Estimer la durée",
        "Planifier par blocs courts",
        "Faire un premier micro-pas",
    ]
    while len(fallback) < steps:
        fallback.append(f"Étape {len(fallback)+1}: vérifier/ajuster")
    return _lines(text, fallback, limit=steps)


def reframe(thought: str) -> List[str]:
    """Reframe syndrome de l'imposteur : recadrages spécifiques à LA pensée donnée."""
    text = _chat(
        f"""Pensée automatique que je rumine : « {thought} »

Donne 4 recadrages courts et SPÉCIFIQUES à cette pensée (pas des platitudes) :
1. Le fait vérifiable qui contredit ou nuance cette pensée.
2. La reformulation probabiliste (remplacer l'absolu par du mesurable).
3. Ce qu'en dirait un ami lucide qui me connaît.
4. La micro-action (<10 min) qui teste cette pensée dans le réel.
Une ligne par recadrage, rien d'autre.""",
        temperature=0.6,
    )
    fallback = [
        "Remplacer l'absolu par du probabiliste",
        "Chercher une preuve contraire",
        "Formuler au présent et spécifique",
        "Transformer en action réaliste",
    ]
    return _lines(text, fallback, limit=4)


def creative(goal: str, mode: str) -> List[str]:
    prompts = {
        "analogies": f"Donne 4 analogies inattendues mais éclairantes pour : « {goal} ». Une par ligne.",
        "prompts": f"Donne 4 consignes créatives stimulantes autour de : « {goal} ». Une par ligne.",
    }
    text = _chat(prompts.get(mode, f"Donne 4 idées originales et actionnables pour : « {goal} ». Une par ligne."), temperature=0.9)
    fallback = [f"Idée 1 pour {goal}", f"Idée 2 pour {goal}", f"Idée 3 pour {goal}"]
    return _lines(text, fallback, limit=4)


def scenarios(context: str, style: str) -> List[str]:
    text = _chat(
        f"""Je dois gérer cette situation sociale : « {context} ». Style souhaité : {style}.

Écris-moi un mini-script en 3 répliques prêtes à dire (ouverture, clarification, sortie),
naturelles et sans sur-politesse. Une réplique par ligne, rien d'autre.""",
        temperature=0.6,
    )
    fallback = [
        f"(Ouverture {style}) Bonjour, j'ai besoin de {context}.",
        f"(Clarification {style}) Ce qui m'aiderait: ...",
        f"(Fermeture {style}) Merci, je reviens vers vous après essai.",
    ]
    return _lines(text, fallback, limit=3)


def psycho_coach(topic: str, style: str) -> str:
    text = _chat(
        f"""Sujet sur lequel j'ai besoin d'un plan d'action : « {topic} ». Ton souhaité : {style}.

Donne un plan en 4 micro-pas maximum (<10 min chacun), spécifique à ce sujet,
puis une phrase d'auto-soutien sobre (pas de positivité forcée). Format compact.""",
        temperature=0.5,
    )
    return text or (
        "Plan d'action (4 micro-pas)\n- Observer 2 min\n- Pas de 3 min\n- Phrase d'auto-soutien\n- Planifier le prochain pas"
    )
