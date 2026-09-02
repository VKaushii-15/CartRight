#!/usr/bin/env bash
set -e
echo "Installing frontend dependencies and building..."
npm --prefix frontend install
npm --prefix frontend run build

PORT=${PORT:-8000}
echo "Starting backend on port $PORT"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
