# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Lumenia — assistant cognitif IA pour profils neuroatypiques (HPI, Asperger/TSA, TDAH). MVP local : backend FastAPI qui sert aussi l'interface (SPA vanilla JS), LLM via fournisseurs gratuits chaînés, SQLite locale. Co-porté par Alex Blanchard et Blandine WYCKAERT.

La référence fonctionnelle est le cahier des charges Google Doc « PROJET LUMENIA : IA POUR HPI, ASPERGER ET PROFILS NEUROATYPIQUES » (id `116quDwGv-XOyVaVQhc1oD1Yvv5n0kOoNlfb3Oel32qA`). En cas de doute sur un comportement produit (portail d'entrée, profilage, sécurité), relire le doc avant de coder — les sections clés sont §3.1 (portail par défis cognitifs), §3.3 (profilage), §3.6 (sécurité psychologique).

## Commandes

```powershell
# Lancer le backend (sert aussi l'UI sur http://127.0.0.1:8000)
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# Vérifier la détection de crise (doit afficher 25/25, exit code 0)
.\backend\.venv\Scripts\python.exe _verify_crisis.py
```

Pas de suite de tests ; `_verify_crisis.py` est le seul harnais et il est **bloquant** : toute modification de `chat.py` doit le laisser à 100 %. Premier setup : `setup_windows_backend.ps1` (crée le venv + dépendances).

Le dossier `frontend/` (Streamlit, port 8502) est **obsolète** depuis la refonte UI de 2026-06 : l'interface vit dans `backend/static/` et est servie par FastAPI. Ne pas y ajouter de features.

## Architecture

Tout le backend est dans `backend/app/`, ~6 fichiers, pas de framework au-delà de FastAPI + SQLAlchemy :

- **`llm.py`** — couche LLM à bascule multi-fournisseurs. `LLM_CHAIN` (dans `.env`) liste des entrées `fournisseur/modèle` essayées dans l'ordre ; un fournisseur sans clé API est sauté au démarrage, une entrée en erreur (429 quota épuisé, 5xx) est mise en cooldown 10 min. C'est la réponse au vrai problème : chaque tier gratuit a des quotas faibles (Gemini 3.5-flash = 20 req/jour ; Cerebras = 1M tokens/jour ; Mistral = 2 req/min) — la chaîne les additionne. Tous les fournisseurs parlent le protocole OpenAI. `max_tokens=3000` minimum : sur Gemini 2.5/3.x les tokens de raisonnement interne comptent dedans, 700 tronque la réponse visible.
- **`chat.py`** — cœur conversationnel. L'analyse de risque est **interne** (jamais de questionnaire affiché) : lexique `_CRISIS_PATTERNS` (FR + EN, texte normalisé sans accents) + formes compactes anti-espacement. Crise détectée → `SAFETY_REPLY` (3114) sans appel LLM + flag `risk.flag` en base → bannière côté UI. Le profil (low_stim, pacing, résultats du parcours d'entrée) est injecté dans le system prompt via `_profile_directives`.
- **`entry.py`** — portail d'entrée : mini-parcours de 4 épreuves (une par dimension : pensée latérale, micro-logique, association abstraite, expression libre) tirées de pools. Les réponses fausses passent par un juge LLM tolérant ; les épreuves « open » n'ont pas de mauvaise réponse. `/entry/complete` stocke les résultats (Assessment `kind=entry` + KV `profile.entry`) qui nourrissent ensuite les prompts du chat. Le parcours filtre sans exclure : skip possible après 3 échecs, terminer ouvre toujours l'accès.
- **`main.py`** — tous les endpoints. État global via la table KV (`consent.accepted`, `risk.flag`, `profile.entry`). Sert `static/index.html` sur `/`.
- **`models.py` / `db.py`** — SQLite `backend/data/lumenia.db` (Postgres possible via `DATABASE_URL`).

L'UI (`backend/static/`) est une SPA sans framework : 3 écrans (consentement → parcours → chat) pilotés par `app.js`. Les conversations sont stockées en `localStorage` (`lumenia.convs`) — cohérent avec la promesse de l'écran de consentement (« tes échanges restent sur cet appareil ») : ne pas introduire de stockage serveur des messages ni de tracking sans repenser ce consentement. Raccourcis : `#seuil` rejoue le parcours d'entrée, `#chat` le saute.

## Contraintes non négociables

- **Sécurité psychologique d'abord** : ne jamais affaiblir la détection de crise, le rappel 3114, ni le gating de `psy_coach` par `risk.flag`. Public vulnérable.
- **Budget 0 €** en phase MVP : rester sur les tiers gratuits ; toute solution qui suppose un abonnement payant doit être validée par Alex.
- **Pas de posture médicale** : Lumenia ne diagnostique pas, ne prescrit pas — ça vaut aussi pour les textes d'UI et les prompts.
- `backend/.env` contient les clés API : jamais dans git (le `.gitignore` l'exclut).
- Interface et réponses LLM en **français**.
