@echo off
cd /d e:\Education\J.A.R.V.I.S

call .venv\Scripts\activate.bat
python -m jarvis_ai.ui.overlay --agent-cmd "python -m jarvis_ai.main"
