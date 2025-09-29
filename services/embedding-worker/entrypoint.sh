#!/usr/bin/env bash
set -euo pipefail

cd /usr/src/app

MODEL_NAME=${EMBEDDING_MODEL_NAME:-BAAI/bge-base-en-v1.5}
CACHE_DIR=${EMBEDDING_CACHE_DIR:-/models}

mkdir -p "$CACHE_DIR"
export SENTENCE_TRANSFORMERS_HOME="$CACHE_DIR"

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

uvicorn app.main:app --host 0.0.0.0 --port "${EMBEDDING_PORT:-9100}"
