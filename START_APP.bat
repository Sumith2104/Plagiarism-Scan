@echo off
echo ===================================================
echo   PlagiaScan - Starting Unified FastAPI Server...
echo ===================================================
echo.

cd /d "c:\Users\hariv\Downloads\Plagiarism-Scan-main\Plagiarism-Scan-main\backend"
start "PlagiaScan Unified App" cmd /k "uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak > nul

echo.
echo ===================================================
echo   The unified application has started!
echo   Open your browser and go to:
echo   http://localhost:8000
echo ===================================================
echo.
pause
