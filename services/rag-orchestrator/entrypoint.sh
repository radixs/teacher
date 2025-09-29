#!/usr/bin/env bash
set -euo pipefail

cd /usr/src/app

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

uvicorn app.main:app \
  --host "${RAG_HOST:-0.0.0.0}" \
  --port "${RAG_PORT:-9000}" \
  ${RAG_RELOAD:+--reload}
