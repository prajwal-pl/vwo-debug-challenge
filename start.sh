#!/bin/bash
# Start all services: Redis, Celery worker, FastAPI server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Financial Document Analyzer ==="

# 1. Start Redis
if redis-cli ping &>/dev/null; then
    echo "[✓] Redis already running"
else
    echo "[*] Starting Redis..."
    redis-server --daemonize yes
    sleep 1
    if redis-cli ping &>/dev/null; then
        echo "[✓] Redis started"
    else
        echo "[✗] Failed to start Redis. Install with: sudo apt install redis-server"
        exit 1
    fi
fi

# 2. Activate venv
source venv/bin/activate

# 3. Start Celery worker in background
echo "[*] Starting Celery worker..."
celery -A tasks_worker worker --loglevel=info --concurrency=2 &>/tmp/celery_worker.log &
CELERY_PID=$!
echo "$CELERY_PID" > /tmp/celery_worker.pid
sleep 3

if kill -0 "$CELERY_PID" 2>/dev/null; then
    echo "[✓] Celery worker started (PID: $CELERY_PID)"
else
    echo "[✗] Celery worker failed to start. Check /tmp/celery_worker.log"
    exit 1
fi

# 4. Start FastAPI
echo "[*] Starting FastAPI server on http://127.0.0.1:8000 ..."
echo ""
echo "    POST /analyze         - Submit document for analysis"
echo "    GET  /status/{task_id} - Poll task status & results"
echo "    GET  /docs            - Swagger UI"
echo ""
echo "Press Ctrl+C to stop all services."
echo "==================================="

# Trap Ctrl+C to clean up
trap 'echo ""; echo "[*] Shutting down..."; kill $CELERY_PID 2>/dev/null; echo "[✓] Done."; exit 0' INT TERM

fastapi dev main.py
