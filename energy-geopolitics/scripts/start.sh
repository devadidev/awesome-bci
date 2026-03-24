#!/bin/sh
# ============================================================
# Start the Energy Geopolitics Intelligence Platform
# ============================================================
# Usage:  sh scripts/start.sh
# Stop:   Ctrl+C

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR"
export LOAD_SEED_DATA=true
export APP_PORT=8000
export APP_LOG_LEVEL=INFO
export CHECKPOINT_DIR="$SCRIPT_DIR/checkpoints"

# Respect PORT env override
PORT="${PORT:-8000}"

echo ""
echo "  ⚡ Energy Geopolitics Intelligence Platform"
echo ""
echo "  Starting server on port $PORT..."
echo "  Open Safari:  http://localhost:$PORT"
echo "  API docs:     http://localhost:$PORT/api/docs"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

python3 -m uvicorn src.main:app \
    --host 127.0.0.1 \
    --port "$PORT" \
    --log-level warning
