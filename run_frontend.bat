@echo off
setlocal
cd /d "%~dp0"
echo ==== LumenIa Frontend (Windows) ====
echo Dossier courant: %CD%
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo Python (py) n'est pas detecte. Installer Python 3.11 via:
  echo   winget install --id Python.Python.3.11 -e
  echo Puis relancer ce script.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0setup_windows_frontend.ps1"
echo.
pause
