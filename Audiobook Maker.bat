@echo off
rem Starts Audiobook Maker on Windows. Double-click this file (it stays in the project folder).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo The app is not set up yet. See "On Windows" in README.md.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" gui.py
