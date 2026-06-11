# Lumenia

Assistant IA pour les personnes neuroatypiques (HPI, Asperger, TDAH).

Un chat qui aide à débloquer une tâche, poser une pensée qui tourne en boucle ou préparer une conversation difficile. Direct, sans jugement, sans jargon médical.

## Lancer

Prérequis : Python 3.12+ et au moins une clé API gratuite (voir `backend/.env.example`, liens inclus).

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # puis coller une clé dedans
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Ouvrir http://127.0.0.1:8000

Sous Windows, `setup_windows_backend.ps1` fait tout ça en un clic. Docker : `docker compose up --build`.

## Comment ça marche

- À l'entrée : consentement, puis un mini-parcours de défis cognitifs (pensée latérale, logique, associations, expression libre). Il sert de seuil symbolique et initialise le profil cognitif, réutilisé ensuite pour adapter les réponses du chat.
- Les conversations restent dans le navigateur (localStorage). Rien n'est envoyé ailleurs que chez le fournisseur LLM.
- Détection de détresse intégrée : si un message évoque des idées suicidaires, Lumenia coupe court et rappelle le 3114.
- Côté LLM : une chaîne de fournisseurs gratuits (Gemini, Cerebras, Groq, Mistral) avec bascule automatique quand un quota est épuisé. Sans aucune clé, l'app reste utilisable en mode dégradé.

La base est une SQLite locale (`backend/data/lumenia.db`). Le dossier `frontend/` est l'ancienne interface Streamlit, plus utilisée : l'UI actuelle est servie directement par le backend.

## Vérifier

```
backend\.venv\Scripts\python _verify_crisis.py
```

Teste la détection de crise — doit afficher 25/25. À relancer après toute modification de `backend/app/chat.py`.

## Important

Lumenia n'est pas un dispositif médical et ne remplace pas un professionnel de santé.
En cas de détresse : **3114** (gratuit, 24h/24) ou **15**.
