#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-run}

case "$COMMAND" in
  run)
    echo "[test] TODO: orchestrate container health checks, API stubs, RAG integration, and UI e2e."
    ;;
  lint)
    echo "[lint] TODO: aggregate formatting and linting commands once services exist."
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    exit 1
    ;;
esac
