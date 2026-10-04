@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Please install dependencies as described in README.md first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "main.py"
