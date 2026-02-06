@echo off
REM Запуск бэкенда (без --reload, чтобы избежать UnicodeDecodeError в дочернем процессе на Windows).
REM Телефон в той же Wi-Fi: откройте http://ВАШ_IP:8000 (ipconfig для IP).

cd /d "%~dp0"
set PYTHONUTF8=1
call .venv\Scripts\activate.bat

REM Port 8000 busy? Run: set PORT=8001 then run this script again
if not defined PORT set PORT=8001
echo Finansly backend: http://0.0.0.0:%PORT%
echo On PC: http://localhost:%PORT%
echo On phone (same Wi-Fi): http://YOUR_IP:%PORT%
echo Restart this script after code changes.
echo.

uvicorn app.main:app --host 0.0.0.0 --port %PORT%

pause
