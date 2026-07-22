#!/usr/bin/env bash
# Restarts the IndusBrain API cleanly.
#
# Needed because uvicorn's --reload watcher intermittently misses edits on this
# Windows setup, and because orphaned ProcessPoolExecutor workers from ingestion
# can inherit the listening socket and keep port 8000 occupied after the parent
# process exits.
set -u

PORT="${1:-8000}"

echo "Stopping anything on port ${PORT}..."
for pid in $(powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort ${PORT} -State Listen -ErrorAction SilentlyContinue).OwningProcess" 2>/dev/null | tr -d '\r'); do
  powershell -NoProfile -Command "Stop-Process -Id ${pid} -Force -ErrorAction SilentlyContinue"
done
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue" 2>/dev/null

sleep 3
find . -name "__pycache__" -path "./app/*" -exec rm -rf {} + 2>/dev/null

echo "Starting API on port ${PORT}..."
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m uvicorn app.main:app \
  --host 127.0.0.1 --port "${PORT}" --log-level info
