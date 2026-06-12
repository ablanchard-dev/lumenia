# Lumenia

Assistant conversationnel pour profils neuroatypiques (HPI, Asperger/TSA, TDAH).

Un chat pour débloquer une tâche, poser une pensée qui tourne en boucle ou préparer
une conversation difficile. Ton direct, sans jugement, sans jargon médical. Backend
FastAPI qui sert aussi l'interface ; LLM via des fournisseurs gratuits chaînés ;
données locales.

## Lancer

Prérequis : Python 3.12+. Au moins une clé API gratuite est conseillée (les liens
sont dans `backend/.env.example`) ; sans clé, l'app reste utilisable en mode dégradé.

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # coller une ou plusieurs clés dedans
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Puis http://127.0.0.1:8000

Sous Windows, `setup_windows_backend.ps1` enchaîne ces étapes. Docker :
`docker compose up --build`.

## Comment ça marche

- **Entrée.** Consentement, puis un parcours de défis cognitifs (pensée latérale,
  logique, raisonnement, similitudes, expression libre). Il conditionne l'accès et
  initialise un profil cognitif réutilisé ensuite pour adapter les réponses du chat.
  Le rappel du 3114 reste accessible à toutes les étapes.
- **Données locales.** Les conversations restent dans le navigateur (localStorage) ;
  rien n'est envoyé ailleurs que chez le fournisseur LLM le temps d'une réponse.
- **Sécurité.** Détection de détresse intégrée : si un message évoque des idées
  suicidaires, Lumenia coupe court et oriente vers le 3114, sans appel au modèle.
- **LLM.** Une chaîne de fournisseurs gratuits (Gemini, Cerebras, Mistral) avec
  bascule automatique quand un quota est épuisé. Tous parlent le protocole OpenAI ;
  un fournisseur sans clé est simplement sauté.

La persistance serveur est une SQLite locale (`backend/data/lumenia.db`). Le dossier
`frontend/` est l'ancienne interface Streamlit, conservée pour mémoire mais plus
utilisée : l'interface actuelle vit dans `backend/static/` et est servie par le
backend.

## Banque du parcours

Les questions d'entrée vivent dans `backend/app/entry_bank.json` (items originaux,
répartis en cinq dimensions). Le script `backend/_verify_bank.py` recalcule de façon
indépendante chaque réponse calculable (suites, arithmétique, jours, logique) et
confirme qu'elle est acceptée par les réponses stockées :

```
cd backend
.venv\Scripts\python _verify_bank.py
```

## Tests

```
cd backend
.venv\Scripts\python -m pytest
```

Couvre la détection de crise et les scores cliniques (`backend/tests/`). La détection
de crise est bloquante : toute modification de `backend/app/chat.py` doit la laisser
au vert.

## Avertissement

Lumenia n'est pas un dispositif médical et ne remplace pas un professionnel de santé.
En cas de détresse : 3114 (gratuit, 24h/24) ou 15.
