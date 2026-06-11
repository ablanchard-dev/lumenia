# Backend one-click setup (Windows PowerShell)
param([switch]$NoPipUpgrade)

Write-Host "== LumenIa Backend setup ==" -ForegroundColor Cyan

# Ensure path
Set-Location -Path "$PSScriptRoot\backend"

# Python check
$pythonOk = $false
try { py --version; $pythonOk = $true } catch { }
if (-not $pythonOk) {
  Write-Warning "Python (py launcher) introuvable. Tentative d'installation via winget..."
  winget install --id Python.Python.3.11 -e
  Write-Host "Relancez ce script après réouverture de PowerShell si la commande py ne fonctionne pas."
  exit 1
}

# venv
py -m venv .venv

# Execution policy (session)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Activate
. .\.venv\Scripts\Activate.ps1

# pip install
if (-not $NoPipUpgrade) { py -m pip install --upgrade pip }
py -m pip install -r requirements.txt

# Create data folder
New-Item -ItemType Directory -Force -Path ".\data" | Out-Null

# Run API
Write-Host "Démarrage API sur http://localhost:8000 ..." -ForegroundColor Green
py -m uvicorn app.main:app --reload --port 8000
