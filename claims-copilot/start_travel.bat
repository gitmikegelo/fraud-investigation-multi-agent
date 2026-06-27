@echo off
echo Starting Claims Copilot (Zurich Travel Guard)...

start "Backend" cmd /k "cd /d %~dp0 && set DOMAIN_MODE=travel && set DEMO_MODE=true && ..\.venv\Scripts\activate && python api.py"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo Mode: TRAVEL GUARD
