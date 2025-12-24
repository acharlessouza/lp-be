#!/usr/bin/env bash

cd /mnt/d/workspace-saas/lp-be
source env/bin/activate

pkill -f 8000
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-1}"

if [ "$RELOAD" = "1" ]; then
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
  exec uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
