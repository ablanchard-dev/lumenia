# Frontend one-click setup (Windows PowerShell)
Write-Host "== LumenIa Frontend setup ==" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\frontend"

# Python check
$pythonOk = $false
try { py --version; $pythonOk = $true } catch { }
if (-not $pythonOk) {
  Write-Warning "Python (py launcher) introuvable. Installez Python (winget) puis relancez."
  exit 1
}

# venv
py -m venv .venv

# Execution policy (session)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Activate
. .\.venv\Scripts\Activate.ps1

# pip install
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# Backend URL env (optionnel)
$env:BACKEND_URL = "http://localhost:8000"

# Run Streamlit
Write-Host "Démarrage UI sur http://localhost:8502 ..." -ForegroundColor Green
streamlit run app.py --server.port 8502
