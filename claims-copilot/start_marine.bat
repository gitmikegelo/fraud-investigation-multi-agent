@echo off
echo Starting Claims Copilot (Marine Cargo)...

start "Backend" cmd /k "cd /d %~dp0 && set "DOMAIN_MODE=marine" && set "DEMO_MODE=true" && set "PYTHONIOENCODING=utf-8" &&..\.venv\Scripts\activate && python api.py"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo Mode: MARINE CARGO (demo mode)
