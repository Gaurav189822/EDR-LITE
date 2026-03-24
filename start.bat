@echo off
chcp 65001 >nul

REM EDR Lite - Quick Start Script for Windows
REM This script starts both backend and frontend servers

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"

echo ========================================================================
echo EDR Lite - Endpoint Detection and Response System
echo ========================================================================

REM Setup and start backend
echo.
echo [SETUP] Setting up backend...
cd /d "%BACKEND_DIR%"

if not exist "venv" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv venv
)

echo [SETUP] Installing backend dependencies...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo [START] Starting backend server...
start "EDR Lite Backend" cmd /k "python main.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Setup and start frontend
echo.
echo [SETUP] Setting up frontend...
cd /d "%FRONTEND_DIR%"

if not exist "node_modules" (
    echo [SETUP] Installing frontend dependencies...
    call npm install
)

echo [START] Starting frontend development server...
start "EDR Lite Frontend" cmd /k "npm run dev"

echo.
echo ========================================================================
echo All services started successfully!
echo ========================================================================
echo.
echo   Backend API:    http://localhost:8000
echo   API Docs:       http://localhost:8000/docs
echo   Dashboard:      http://localhost:3000
echo.
echo Close the command windows to stop the services
echo.

pause