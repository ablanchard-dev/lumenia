@echo off
cd /d "%~dp0"
start powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command "Set-Location -Path '%~dp0'"
