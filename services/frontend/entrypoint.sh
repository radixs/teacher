#!/usr/bin/env sh
set -euo pipefail

cd /usr/src/app

if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

PORT="${FRONTEND_INTERNAL_PORT:-3000}"
exec npm run dev -- --host 0.0.0.0 --port "$PORT"
