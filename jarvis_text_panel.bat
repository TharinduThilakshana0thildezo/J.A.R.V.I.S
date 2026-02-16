@echo off
cd /d e:\Education\J.A.R.V.I.S

REM Text panel: force JARVIS into text-only input mode
set JARVIS_TEXT_ONLY=1

call .venv\Scripts\activate.bat
python -m jarvis_ai.main

echo.
echo JARVIS has exited. If there was an error, it is shown above.
echo Press any key to close this window...
pause >nul
