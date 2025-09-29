# syntax=docker/dockerfile:1.6

ARG UBUNTU_VERSION=22.04
ARG LLAMA_CPP_REF=b3309

FROM ubuntu:${UBUNTU_VERSION} AS builder

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git clone https://github.com/ggerganov/llama.cpp.git \
    && cd llama.cpp \
    && git checkout ${LLAMA_CPP_REF} \
    && cmake -B build -S . -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_EXAMPLES=OFF \
    && cmake --build build -j "$(nproc)" \
    && strip build/bin/llama-server

FROM ubuntu:${UBUNTU_VERSION} AS runtime

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python3 \
        python3-pip \
    && pip3 install --no-cache-dir pyyaml \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server

WORKDIR /srv

COPY config.yaml /defaults/config.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV LLM_CONFIG_PATH=/config/config.yaml \
    LLM_MODELS_DIR=/models \
    LLM_DOWNLOAD_CONCURRENCY=1

VOLUME ["/models"]

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
