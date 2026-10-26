#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -z "${SENTINEL_PYTHON:-}" ]; then
  if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
    .venv/bin/python -m pip install -e './backend[test]'
  fi
  SENTINEL_PYTHON="$PWD/.venv/bin/python"
fi
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm ci)
fi
(cd frontend && npm run build)
export PYTHONPATH="$PWD/backend${PYTHONPATH:+:$PYTHONPATH}"
export SENTINEL_DB="${SENTINEL_DB:-$PWD/sentinel.sqlite3}"
exec "$SENTINEL_PYTHON" -m uvicorn sentinel.api:app --host 127.0.0.1 --port "${PORT:-8000}" --timeout-graceful-shutdown 2
