@echo off
echo ===================================================
echo       AI Financial Analyst - System Launcher
echo ===================================================
echo.

echo [1/3] Starting Backend Server (Port 8000)...
start "AI Financial Analyst Backend" cmd /k "uvicorn app.main:app --reload --port 8000"

echo [2/3] Starting Frontend Dashboard (Port 3000)...
cd frontend
start "AI Financial Analyst Frontend" cmd /k "npm run dev"

echo [3/3] Opening Dashboard in Browser...
timeout /t 5 >nul
start http://localhost:3000

echo.
echo ===================================================
echo       System is Running!
echo       Backend: http://localhost:8000/docs
echo       Frontend: http://localhost:3000
echo ===================================================
pause
