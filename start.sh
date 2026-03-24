#!/bin/bash

# EDR Lite - Quick Start Script
# This script starts both backend and frontend servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "========================================================================"
echo "EDR Lite - Endpoint Detection and Response System"
echo "========================================================================"

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping all services..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "[DONE] All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Setup and start backend
echo ""
echo "[SETUP] Setting up backend..."
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "[SETUP] Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "[SETUP] Installing backend dependencies..."
./venv/bin/pip install -q -r requirements.txt

echo "[START] Starting backend server..."
./venv/bin/python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Setup and start frontend
echo ""
echo "[SETUP] Setting up frontend..."
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "[SETUP] Installing frontend dependencies..."
    npm install
fi

echo "[START] Starting frontend development server..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================================================"
echo "All services started successfully!"
echo "========================================================================"
echo ""
echo "  Backend API:    http://localhost:8000"
echo "  API Docs:       http://localhost:8000/docs"
echo "  Dashboard:      http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait