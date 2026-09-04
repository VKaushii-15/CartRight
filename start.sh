PORT=${PORT:-8000}
echo "Starting backend on port $PORT"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
