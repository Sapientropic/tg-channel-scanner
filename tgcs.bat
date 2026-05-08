@echo off
setlocal

set "ROOT_DIR=%~dp0"

if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT_DIR%.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" "%ROOT_DIR%scripts\tgcs.py" %*
exit /b %ERRORLEVEL%
