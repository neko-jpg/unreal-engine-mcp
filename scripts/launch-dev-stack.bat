@echo off
REM Windows wrapper for launch-dev-stack.py
REM Double-click from Explorer or run from Command Prompt

cd /d "%~dp0\.."
python scripts\launch-dev-stack.py %*
if errorlevel 1 pause
