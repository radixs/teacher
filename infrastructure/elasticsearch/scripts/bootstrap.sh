#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"

configure_single_node_dev_cluster() {
  echo "Configuring single-node development cluster settings" >&2
  curl -sS -X PUT "$ES_URL/_cluster/settings" \
    -H 'Content-Type: application/json' \
    --data-binary @- <<'JSON' | jq '.'
{
  "persistent": {
    "cluster.routing.allocation.disk.threshold_enabled": false
  }
}
JSON
}

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

ensure_index() {
  local name="$1"
  local response
  local properties_count
  local status

  status=$(curl -s -o /dev/null -w '%{http_code}' "$ES_URL/$name")
  if [ "$status" = "200" ]; then
    echo "Index already exists: $name" >&2
    response=$(curl -sS "$ES_URL/$name")
    printf '%s\n' "$response" | jq '.'
    properties_count=$(printf '%s\n' "$response" | jq 'to_entries[0].value.mappings.properties // {} | length')

    if [ "$properties_count" = "0" ]; then
      echo "Index $name exists but has no mapped properties. It was likely created before the template fix. Delete the index and rerun make bootstrap-es." >&2
      return 1
    fi

    return 0
  fi

  echo "Creating index: $name" >&2
  curl -sS -X PUT "$ES_URL/$name" | jq '.'
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../indices"

configure_single_node_dev_cluster

for template in "$TEMPLATES_DIR"/*.json; do
  apply_template "$template"
  echo
  sleep 1
done

# Create indices explicitly to ensure availability
ensure_index "user_profiles"
ensure_index "knowledge_snapshots"
ensure_index "learning_resources"
ensure_index "dependency_graph"
ensure_index "session_interactions"
ensure_index "sessions"
