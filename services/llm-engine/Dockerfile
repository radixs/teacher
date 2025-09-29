# syntax=docker/dockerfile:1.6

ARG UBUNTU_VERSION=22.04
ARG ROCM_VERSION=5.7.1
ARG LLAMA_CPP_REF=b3309

FROM rocm/dev-ubuntu-${UBUNTU_VERSION}:${ROCM_VERSION} AS builder

ENV DEBIAN_FRONTEND=noninteractive     ROCM_PATH=/opt/rocm

RUN apt-get update     && apt-get install -y --no-install-recommends         build-essential         cmake         git         wget         python3         python3-pip         libcurl4-openssl-dev         pkg-config     && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git clone https://github.com/ggerganov/llama.cpp.git     && cd llama.cpp     && git checkout ${LLAMA_CPP_REF}     && cmake -B build -S .         -DLLAMA_BUILD_SERVER=ON         -DLLAMA_BUILD_EXAMPLES=OFF         -DLLAMA_CURL=ON         -DLLAMA_HIPBLAS=ON     && cmake --build build -j "$(nproc)"     && cmake --install build --prefix /opt/llama     && strip build/bin/llama-server

FROM rocm/dev-ubuntu-${UBUNTU_VERSION}:${ROCM_VERSION} AS runtime

ENV DEBIAN_FRONTEND=noninteractive     ROCM_PATH=/opt/rocm     HSA_OVERRIDE_GFX_VERSION=10.3.0     HIP_VISIBLE_DEVICES=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python3 \
        python3-pip \
        libcurl4 \
        rocblas-dev \
        hipblas \
    && pip3 install --no-cache-dir pyyaml \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/llama /opt/llama
RUN cp /opt/llama/bin/llama-server /usr/local/bin/llama-server     && cp /opt/llama/lib/*.so /usr/local/lib/     && ldconfig

WORKDIR /srv

RUN mkdir -p /config
COPY config.yaml /config/config.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV LLM_CONFIG_PATH=/config/config.yaml     LLM_MODELS_DIR=/models     LLM_DOWNLOAD_CONCURRENCY=1

VOLUME ["/models"]

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
