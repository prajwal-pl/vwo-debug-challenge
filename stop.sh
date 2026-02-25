#!/bin/bash
# Stop all services: Celery worker, FastAPI, Redis

echo "=== Stopping Services ==="

# Stop FastAPI (anything on port 8000)
if lsof -ti:8000 &>/dev/null; then
    kill $(lsof -ti:8000) 2>/dev/null
    echo "[✓] FastAPI stopped"
else
    echo "[-] FastAPI not running"
fi

# Stop Celery worker
if [ -f /tmp/celery_worker.pid ]; then
    CELERY_PID=$(cat /tmp/celery_worker.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        kill "$CELERY_PID" 2>/dev/null
        echo "[✓] Celery worker stopped (PID: $CELERY_PID)"
    else
        echo "[-] Celery worker not running"
    fi
    rm -f /tmp/celery_worker.pid
else
    # Try pkill as fallback
    pkill -f "celery.*tasks_worker" 2>/dev/null && echo "[✓] Celery worker stopped" || echo "[-] Celery worker not running"
fi

# Stop Redis
if redis-cli ping &>/dev/null; then
    redis-cli shutdown 2>/dev/null
    echo "[✓] Redis stopped"
else
    echo "[-] Redis not running"
fi

echo "=== All services stopped ==="
