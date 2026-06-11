#!/usr/bin/env bash
set -e
case "$1" in
  backend)
    cd "$(dirname "$0")/backend"
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    mkdir -p data
    uvicorn app.main:app --reload --port 8000
    ;;
  frontend)
    cd "$(dirname "$0")/frontend"
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    export BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
    streamlit run app.py --server.port 8502
    ;;
  *)
    echo "Usage: ./setup.sh backend|frontend"
    ;;
esac
