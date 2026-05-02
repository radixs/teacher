#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"

apply_template() {
  local file="$1"
  local name
  name=$(basename "$file" .json)
  echo "Applying template: $name" >&2
  curl -sS -X PUT "$ES_URL/_index_template/$name" \
    -H 'Content-Type: application/json' \
    --data-binary "@$file" \
    | jq '.'
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../indices"

for template in "$TEMPLATES_DIR"/*.json; do
  apply_template "$template"
  echo
  sleep 1
fi

# Create indices explicitly to ensure availability
curl -sS -X PUT "$ES_URL/user_profiles" | jq '.'
curl -sS -X PUT "$ES_URL/knowledge_snapshots" | jq '.'
curl -sS -X PUT "$ES_URL/learning_resources" | jq '.'
curl -sS -X PUT "$ES_URL/dependency_graph" | jq '.'
curl -sS -X PUT "$ES_URL/session_interactions" | jq '.'
curl -sS -X PUT "$ES_URL/sessions" | jq '.'
