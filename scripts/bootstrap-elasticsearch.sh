#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for JSON formatting. Please install jq." >&2
  exit 1
fi

ES_URL=${ELASTICSEARCH_URL:-http://localhost:9200}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$BASE_DIR/infrastructure/elasticsearch"

if ! curl -s "$ES_URL" >/dev/null; then
  echo "Elasticsearch not reachable at $ES_URL" >&2
  exit 1
fi

"$CONFIG_DIR/scripts/bootstrap.sh"
