@echo off
echo Open http://127.0.0.1:8000 in Chrome after the server starts.
echo Keep this window open while using the trainer.
cd /d "%~dp0radar-trainer"
".venv\Scripts\python.exe" run_openai.py
pause
