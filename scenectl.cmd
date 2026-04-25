@echo off
setlocal
set "REPO_ROOT=%~dp0"
python "%REPO_ROOT%scripts\scenectl.py" %*
