#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for JSON formatting. Please install jq." >&2
  exit 1
fi

ES_URL=${ELASTICSEARCH_URL:-http://localhost:9200}
export ELASTICSEARCH_URL="$ES_URL"
MAX_ATTEMPTS=${ELASTICSEARCH_BOOTSTRAP_ATTEMPTS:-30}
SLEEP_SECONDS=${ELASTICSEARCH_BOOTSTRAP_SLEEP_SECONDS:-2}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$BASE_DIR/infrastructure/elasticsearch"

attempt=1
until curl -fsS "$ES_URL/_cluster/health?wait_for_status=yellow&timeout=1s" >/dev/null; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "Elasticsearch not reachable or not ready at $ES_URL after $MAX_ATTEMPTS attempts" >&2
    exit 1
  fi

  echo "Waiting for Elasticsearch at $ES_URL (attempt $attempt/$MAX_ATTEMPTS)..." >&2
  sleep "$SLEEP_SECONDS"
  attempt=$((attempt + 1))
done

"$CONFIG_DIR/scripts/bootstrap.sh"
