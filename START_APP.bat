@echo off
echo ===================================================
echo   PlagiaScan - Starting Unified FastAPI Server...
echo ===================================================
echo.

cd /d "%~dp0backend"
start "PlagiaScan Unified App" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak > nul

echo.
echo ===================================================
echo   The unified application has started!
echo   Open your browser at:
echo     - Localhost:    http://localhost:8000
echo     - sslip.io:     http://127.0.0.1.sslip.io:8000
echo ===================================================
echo.
pause
