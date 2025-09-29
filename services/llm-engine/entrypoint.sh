#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${LLM_CONFIG_PATH:-/config/config.yaml}"
DEFAULT_CONFIG="/defaults/config.yaml"

if [ ! -f "$CONFIG_PATH" ]; then
  echo "[llm-engine] No config at $CONFIG_PATH. Using default." >&2
  mkdir -p "$(dirname "$CONFIG_PATH")"
  cp "$DEFAULT_CONFIG" "$CONFIG_PATH"
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

MODEL_DIR="$(dirname "$MODEL_PATH")"
mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_PATH" ]; then
  echo "[llm-engine] Downloading model from $MODEL_URL" >&2
  curl -L "$MODEL_URL" -o "$MODEL_PATH"
fi

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

exec "${CMD[@]}"
