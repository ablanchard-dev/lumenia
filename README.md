# Lumenia

Conversational assistant for neurodivergent profiles (gifted/HPI, Asperger/ASD, ADHD).

A chat to unblock a task, put down a looping thought, or prepare a difficult
conversation. Direct tone, no judgment, no medical jargon. A FastAPI backend that also
serves the UI; an LLM via chained free providers; local data.

## Run

Requirements: Python 3.12+. At least one free API key is recommended (links are in
`backend/.env.example`); without a key, the app still works in a degraded mode.

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # paste one or more keys into it
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Then http://127.0.0.1:8000

On Windows, `setup_windows_backend.ps1` chains these steps. Docker:
`docker compose up --build`.

## How it works

- **Entry.** Consent, then a short run of cognitive challenges across six WAIS-inspired
  dimensions (verbal comprehension, fluid reasoning, working memory, visuospatial
  reasoning, processing speed, free expression), mostly multiple-choice with a few open
  answers. It initializes a cognitive profile reused afterwards to adapt the chat's
  answers, and the SPA only reveals the chat once the run clears the pass threshold.
  This gate is client-side: server-side enforcement is not yet wired (the API does not
  block `/chat` on the entry result) — WIP. The 3114 reminder stays reachable at every
  step.
- **Local data.** Conversations stay in the browser (localStorage), and message
  content is only sent to the LLM provider for the duration of a response. Two things do
  persist server-side in the local SQLite: the entry-test answers (cognitive profile)
  and a risk flag set by the crisis check.
- **Safety.** Built-in distress detection: if a message hints at suicidal thoughts,
  Lumenia stops short and points to 3114, without calling the model.
- **LLM.** A chain of free providers (Gemini, Cerebras, Mistral) with automatic
  failover when a quota runs out. They all speak the OpenAI protocol; a provider with
  no key is simply skipped.

Server persistence is a local SQLite (`backend/data/lumenia.db`). The `frontend/`
folder is the old Streamlit interface, kept for reference but no longer used: the
current UI lives in `backend/static/` and is served by the backend.

## Entry question bank

The entry questions live in `backend/app/entry_bank.json` — about 300 original items
across six dimensions, mostly multiple-choice plus some open answers (original items
only: real psychometric tests are copyrighted and clinically reserved). The
`backend/_verify_bank.py` script independently recomputes every computable answer
(sequences, arithmetic, days, logic) and checks the multiple-choice items structurally
(the key points to a real, non-empty, distinct choice):

```
cd backend
.venv\Scripts\python _verify_bank.py
```

## Tests

```
cd backend
.venv\Scripts\python -m pytest
```

Covers crisis detection and clinical scores (`backend/tests/`). The clinical scores are
legacy assessment endpoints (PHQ-9/GAD-7), not used by the current UI. Crisis detection
is blocking: any change to `backend/app/chat.py` must keep it green.

## Disclaimer

Lumenia is not a medical device and does not replace a health professional. In
distress: 3114 (France's national suicide-prevention line, free, 24/7) or 15 (medical
emergencies).
