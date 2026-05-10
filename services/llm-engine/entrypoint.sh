#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${LLM_CONFIG_PATH:-/config/config.yaml}"
DEFAULT_CONFIG="/defaults/config.yaml"
FLOW_LOG_PATH="${FLOW_LOG_PATH:-}"
FLOW_EVENT_PUSH_URL="${FLOW_EVENT_PUSH_URL:-}"
FLOW_EVENT_TOKEN="${FLOW_EVENT_TOKEN:-}"

push_flow_event() {
  local timestamp="$1"
  local step="$2"
  local message="$3"
  local context="${4:-}"

  if [ -z "$FLOW_EVENT_PUSH_URL" ]; then
    return
  fi

  python3 - "$timestamp" "$step" "$message" "$context" "$FLOW_EVENT_PUSH_URL" "$FLOW_EVENT_TOKEN" <<'PY'
import json
import sys
from urllib import error as urllib_error
from urllib import request as urllib_request

timestamp, step, message, context_raw, url, token = sys.argv[1:7]
payload = {
    "timestamp": timestamp,
    "service": "llm-engine",
    "step": step,
    "message": message,
    "context": {},
}

if context_raw:
    try:
        payload["context"] = json.loads(context_raw)
    except json.JSONDecodeError:
        payload["context"] = {"raw": context_raw}

request = urllib_request.Request(
    url,
    data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
    method="POST",
)

if token:
    request.add_header("X-Flow-Event-Token", token)

try:
    with urllib_request.urlopen(request, timeout=0.5) as response:
        response.read()
except (urllib_error.URLError, TimeoutError, OSError):
    pass
PY
}

log_flow() {
  local step="$1"
  local message="$2"
  local context="${3:-}"
  local timestamp

  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  if [ -z "$FLOW_LOG_PATH" ]; then
    push_flow_event "$timestamp" "$step" "$message" "$context"
    return
  fi

  mkdir -p "$(dirname "$FLOW_LOG_PATH")"
  touch "$FLOW_LOG_PATH"
  chmod 666 "$FLOW_LOG_PATH" 2>/dev/null || true

  if [ -n "$context" ]; then
    printf '%s | llm-engine | %s | %s | %s\n' \
      "$timestamp" \
      "$step" \
      "$message" \
      "$context" >> "$FLOW_LOG_PATH"
  else
    printf '%s | llm-engine | %s | %s\n' \
      "$timestamp" \
      "$step" \
      "$message" >> "$FLOW_LOG_PATH"
  fi

  push_flow_event "$timestamp" "$step" "$message" "$context"
}

if [ ! -f "$CONFIG_PATH" ]; then
  echo "[llm-engine] No config at $CONFIG_PATH. Using default." >&2
  mkdir -p "$(dirname "$CONFIG_PATH")"
  cp "$DEFAULT_CONFIG" "$CONFIG_PATH"
  log_flow "config.defaulted" "LLM engine did not find a config file and copied the default config into place."
fi

read_yaml() {
  local key="$1"
  python3 - "$CONFIG_PATH" "$key" <<'PY'
import sys
from pathlib import Path
import yaml
config_path = Path(sys.argv[1])
key = sys.argv[2]
with config_path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
value = data
for part in key.split('.'):
    value = value[part]
print(value)
PY
}

MODEL_PATH=${LLM_MODEL_PATH:-$(read_yaml 'model.path')}
MODEL_URL=${LLM_MODEL_URL:-$(read_yaml 'model.url')}
HOST=${LLM_SERVER_HOST:-$(read_yaml 'server.host')}
PORT=${LLM_SERVER_PORT:-$(read_yaml 'server.port')}
CONTEXT=${LLM_CONTEXT_WINDOW:-$(read_yaml 'server.context_length')}
GPU_LAYERS=${LLM_GPU_LAYERS:-$(read_yaml 'server.gpu_layers')}
THREADS=${LLM_THREADS:-$(read_yaml 'server.threads')}
BATCH_SIZE=${LLM_BATCH_SIZE:-$(read_yaml 'server.batch_size')}
ACCELERATION_MODE_RAW=${LLM_ACCELERATION_MODE:-gpu}
ACCELERATION_MODE=$(printf '%s' "$ACCELERATION_MODE_RAW" | tr '[:upper:]' '[:lower:]')

MODEL_DIR="$(dirname "$MODEL_PATH")"
mkdir -p "$MODEL_DIR"

log_flow "config.loaded" "LLM engine loaded its startup configuration and resolved model/runtime settings."

if [ ! -f "$MODEL_PATH" ]; then
  echo "[llm-engine] Downloading model from $MODEL_URL" >&2
  log_flow "model.download.started" "LLM engine is downloading the GGUF model file before serving requests."
  curl -L "$MODEL_URL" -o "$MODEL_PATH"
  log_flow "model.download.completed" "LLM engine finished downloading the GGUF model file."
fi

case "$ACCELERATION_MODE" in
  gpu)
    ;;
  cpu)
    GPU_LAYERS=0
    export HIP_VISIBLE_DEVICES=-1
    ;;
  *)
    echo "[llm-engine] Unsupported LLM_ACCELERATION_MODE='$ACCELERATION_MODE_RAW'. Use 'gpu' or 'cpu'." >&2
    exit 1
    ;;
esac

CMD=(
  "llama-server"
  "--model" "$MODEL_PATH"
  "--host" "$HOST"
  "--port" "$PORT"
  "--ctx-size" "$CONTEXT"
  "--threads" "$THREADS"
  "--batch-size" "$BATCH_SIZE"
)

if [ "${GPU_LAYERS}" != "0" ]; then
  CMD+=("--gpu-layers" "$GPU_LAYERS")
fi

log_flow "runtime.mode.selected" "LLM engine selected its acceleration mode before launching llama.cpp." \
  " | {\"mode\":\"${ACCELERATION_MODE}\",\"gpu_layers\":${GPU_LAYERS},\"hip_visible_devices\":\"${HIP_VISIBLE_DEVICES:-}\"}"
log_flow "server.starting" "LLM engine is starting the llama.cpp server process."

exec "${CMD[@]}"
