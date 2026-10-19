@echo off
title SupportOps AI Agent
cd /d "%~dp0"

echo ===================================================
echo       Iniciando SupportOps AI Agent...
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)

pause
