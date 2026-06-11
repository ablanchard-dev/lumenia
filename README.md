# Lumenia v2.1 (FIX) — Démarrage en 2 scripts

Deux dossiers **séparés** :
- `backend/` (FastAPI) — port 8000
- `frontend/` (Streamlit) — port 8502

## Lancement express (Windows)
Clique droit → **Exécuter avec PowerShell** sur:
- `setup_windows_backend.ps1`
- `setup_windows_frontend.ps1`

(Chaque script crée un venv, installe les dépendances et démarre le service.)

## Lancement express (Mac/Linux)
```bash
chmod +x setup.sh
./setup.sh backend
./setup.sh frontend
```

## Si besoin de Docker
```bash
docker compose up --build
```

DB: SQLite locale (`backend/data/lumenia.db`).  
Changer pour Postgres: définir `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname` **avant** de lancer le backend.
