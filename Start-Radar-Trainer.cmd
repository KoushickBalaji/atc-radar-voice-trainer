@echo off
setlocal
set "TRAINER_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%TRAINER_PYTHON%" set "TRAINER_PYTHON=%~dp0radar-trainer\.venv\Scripts\python.exe"
if not exist "%TRAINER_PYTHON%" (
    echo Python virtual environment not found.
    echo Expected .venv\Scripts\python.exe in the project root or radar-trainer folder.
    pause
    exit /b 1
)
echo Open http://127.0.0.1:8000 in Chrome after the server starts.
echo Keep this window open while using the trainer.
cd /d "%~dp0radar-trainer" || exit /b 1
"%TRAINER_PYTHON%" run_openai.py
pause
