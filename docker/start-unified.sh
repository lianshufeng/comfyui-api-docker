#!/usr/bin/env bash
set -Eeuo pipefail

model_dir=/models
model_name=SenseNova-U1.5-8B-MoT-T8-int8-convrot-tagged.safetensors
lora_name=SenseNova-U1.5-8B-MoT-LoRA-8step-ComfyUI.safetensors

for model_file in "$model_name" "$lora_name"; do
    if [[ ! -f "$model_dir/$model_file" ]]; then
        echo "Missing model file: $model_dir/$model_file" >&2
        exit 1
    fi
done

mkdir -p \
    /opt/ComfyUI/input \
    /opt/ComfyUI/output \
    /opt/ComfyUI/user \
    /opt/ComfyUI/models/diffusion_models/SenseNovaU1.5 \
    /opt/ComfyUI/models/loras \
    /root/comfyui-api-runs \
    /root/comfyui-api-data

ln -sfn "$model_dir/$model_name" "/opt/ComfyUI/models/diffusion_models/SenseNovaU1.5/$model_name"
ln -sfn "$model_dir/$lora_name" "/opt/ComfyUI/models/loras/$lora_name"

/opt/venv/bin/python /opt/ComfyUI/main.py --listen 0.0.0.0 --port 8188 ${CLI_ARGS:-} &
comfy_pid=$!

for _ in $(seq 1 180); do
    if /opt/venv/bin/python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)' >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "$comfy_pid" 2>/dev/null; then
        wait "$comfy_pid" || true
        exit 1
    fi
    sleep 1
done

if ! /opt/venv/bin/python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)' >/dev/null 2>&1; then
    echo "ComfyUI did not become ready within 180 seconds" >&2
    exit 1
fi

API_LISTEN=0.0.0.0 \
API_PORT=8460 \
COMFYUI_BASE_URL=http://127.0.0.1:8188 \
COMFYUI_STARTUP_CHECK=true \
WORKFLOWS_DIR=/opt/comfyui-api-workflows \
RUNS_DIR=/root/comfyui-api-runs \
DATA_DIR=/root/comfyui-api-data \
IMAGE_UPLOAD_MODE=comfy \
INPUT_SUBDIR=comfyui2api \
WORKER_CONCURRENCY=1 \
API_TOKEN="${SENSENOVA_API_TOKEN:-}" \
COMFYUI2API_UI_ENABLED=false \
/opt/venv/bin/python -m comfyui2api serve --disable-ui &
api_pid=$!

shutdown() {
    trap - TERM INT EXIT
    kill "$api_pid" "$comfy_pid" 2>/dev/null || true
    wait "$api_pid" "$comfy_pid" 2>/dev/null || true
}
trap shutdown TERM INT EXIT

set +e
wait -n "$api_pid" "$comfy_pid"
status=$?
set -e
shutdown
exit "$status"
