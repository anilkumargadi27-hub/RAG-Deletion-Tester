#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " ForgetCheck — RAG Deletion & Access-Revocation Tester   "
echo " Tagline: Check what your AI can still reveal after access changes."
echo "=========================================================="

if [ -f ".venv/bin/activate" ]; then
    echo "[1/4] Activating Python virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[2/4] Initializing and seeding demo data..."
export PYTHONPATH="."
python scripts/seed_demo.py

if [ ! -f "frontend/dist/index.html" ]; then
    echo "[3/4] Building production frontend assets..."
    cd frontend && npm run build && cd ..
else
    echo "[3/4] Production frontend build verified."
fi

PORT="${PORT:-8000}"
echo "[4/4] Starting ForgetCheck on http://localhost:$PORT..."
echo ""
echo "Local URLs:"
echo " - Web Application: http://localhost:$PORT"
echo " - Health Check:    http://localhost:$PORT/health"
echo " - API Specs:       http://localhost:$PORT/docs"
echo ""
echo "Demo Accounts:"
echo " - Admin:   admin   / Admin@ForgetCheck2026!"
echo " - Auditor: auditor / Auditor@ForgetCheck2026!"
echo " - Member:  member  / Member@ForgetCheck2026!"
echo ""

exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
