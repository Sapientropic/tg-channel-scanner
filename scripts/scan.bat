@echo off
REM Batch-read Telegram channels (Windows)
REM Usage: scripts\scan.bat <channel_list.txt> [hours]

cd /d "%~dp0\.."

set LIST=%1
set HOURS=%2
if "%HOURS%"=="" set HOURS=24

call .venv\Scripts\activate.bat

for /f %%i in ('python -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=%HOURS%)).strftime('%%Y-%%m-%%d'))"') do set AFTER=%%i

if not exist "output" mkdir output
for /f %%i in ('python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).strftime('%%Y%%m%%d_%%H%%M'))"') do set TS=%%i
set OUTPUT=output\scan_%TS%.jsonl

echo Time window: past %HOURS%h (since %AFTER%)
echo Output: %OUTPUT%

for /f "usebackq eol=# delims=" %%ch in ("%LIST%") do (
    echo Reading: %%ch
    tg read "%%ch" --after %AFTER% --limit 100 >> "%OUTPUT%" 2>&1
    timeout /t 1 /nobreak >nul
)

echo Done. Output: %OUTPUT%
