FROM ghcr.io/astral-sh/uv:0.8.17 AS uv
FROM nvidia/cuda:12.6.3-base-ubuntu22.04

COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_HTTP_TIMEOUT=1800 UV_HTTP_RETRIES=5

RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends ca-certificates git libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ARG PYTHON_VERSION=3.12.11
RUN uv python install "${PYTHON_VERSION}" \
    && uv venv --python "${PYTHON_VERSION}" /opt/venv

ARG PYTORCH_VERSION=2.8.0
ARG TORCHVISION_VERSION=0.23.0
ARG TORCHAUDIO_VERSION=2.8.0
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python \
       "torch==${PYTORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}" "torchaudio==${TORCHAUDIO_VERSION}" \
       --index-url https://download.pytorch.org/whl/cu126

ARG COMFYUI_BRANCH=master
RUN --mount=type=cache,target=/root/.cache/uv \
    for attempt in 1 2 3 4 5; do \
        git clone --branch "${COMFYUI_BRANCH}" --depth 1 https://github.com/Comfy-Org/ComfyUI.git /opt/ComfyUI && break; \
        rm -rf /opt/ComfyUI; \
        if [ "${attempt}" -eq 5 ]; then exit 1; fi; \
        sleep "$((attempt * 5))"; \
    done \
    && uv pip install --python /opt/venv/bin/python -r /opt/ComfyUI/requirements.txt \
    && rm -rf /opt/ComfyUI/.git

ARG SENSENOVA_NODES_VERSION=1.3.1
COPY docker/custom_nodes/ComfyUI-SenseNova-U1.5-ConvRot /opt/ComfyUI/custom_nodes/ComfyUI-SenseNova-U1.5-ConvRot
LABEL org.opencontainers.image.sensenova-node-version="${SENSENOVA_NODES_VERSION}"

ARG COMFYUI2API_VERSION=v0.0.0-action-test-20260530-0323876
RUN --mount=type=cache,target=/root/.cache/uv \
    for attempt in 1 2 3 4 5; do \
        git clone --branch "${COMFYUI2API_VERSION}" --depth 1 https://github.com/Einzieg/Comfyui2api.git /opt/comfyui2api && break; \
        rm -rf /opt/comfyui2api; \
        if [ "${attempt}" -eq 5 ]; then exit 1; fi; \
        sleep "$((attempt * 5))"; \
    done \
    && uv pip install --python /opt/venv/bin/python /opt/comfyui2api \
    && rm -rf /opt/comfyui2api/.git

RUN mkdir -p /opt/ComfyUI/user/default/workflows /opt/comfyui-api-workflows

COPY docker/prepare-model.py /usr/local/bin/prepare-model.py
COPY docker/start-unified.sh /usr/local/bin/start-unified.sh
RUN chmod +x /usr/local/bin/start-unified.sh

EXPOSE 8188 8460
ENTRYPOINT ["/usr/local/bin/start-unified.sh"]
