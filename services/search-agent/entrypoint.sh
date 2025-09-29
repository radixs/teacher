#!/usr/bin/env bash
set -euo pipefail

cd /usr/src/app

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

uvicorn app.main:app --host 0.0.0.0 --port "${SEARCH_AGENT_PORT:-9205}"
