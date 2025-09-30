# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY lab_templates ./lab_templates
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV RAG_APP_NAME="RAG Orchestrator" \
    RAG_HOST=0.0.0.0 \
    RAG_PORT=9000

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
