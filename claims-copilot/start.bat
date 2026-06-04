@echo off
echo Starting Claims Copilot...

start "Backend" cmd /k "cd /d %~dp0 && ..\.venv\Scripts\activate && python api.py"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
