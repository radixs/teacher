# Teacher App Scaffold

This repository hosts a containerized learning companion that guides users through custom training paths using Retrieval-Augmented Generation (RAG) backed by Elasticsearch. The stack comprises a Vue 3 SPA, Laravel 12 API, and Python microservices coordinating local LLM + embedding models that run comfortably on an AMD Ryzen 5 7600 / Radeon RX 6600 workstation.

## Status
Calibration flow implemented: sessions begin with guided questions whose answers are stored in Elasticsearch for later tuning.
Tuning roadmap generator creates a dependency list after calibration and stores it in Elasticsearch.
The project is in the bootstrap phase. Core services, orchestration scripts, and documentation are being scaffolded according to the rollout plan in `rollout.md`.

## Prerequisites
- Docker Engine 24+
- Docker Compose plugin 2.20+
- GNU Make 4+
- Git LFS (optional, for large model binaries)

Copy the environment template before running any commands:

```bash
cp .env.dist .env
```

Populate credentials and tune resource-specific variables as needed.

## Make Targets
- `make build` – build all service images.
- `make up` – start the full stack in detached mode.
- `make down` – stop and remove containers.
- `make logs` – follow logs from all services.
- `make test` – execute the verification suite (to be implemented).

## Service Overview

After bringing the stack up, run `make bootstrap-es` to apply Elasticsearch index templates.
| Service | Role | Tech |
| --- | --- | --- |
| frontend | Chat UI, lesson flow, progress visualizations | Vue 3 + Vuex (Vite) |
| backend | Session management, persistence, API gateway | Laravel 12 |
| rag-orchestrator | Prompt assembly, context retrieval, evaluation | FastAPI |
| llm-engine | Hosts mistral-7b-instruct via llama.cpp (configurable via `services/llm-engine/config.yaml`, models cached under `llm_models` volume) | C++/llama.cpp |
| embedding-worker | Generates `bge-base-en-v1.5` embeddings (FastAPI microservice, caches models under `embedding_models` volume) | Python + sentence-transformers |
| search-agent | DuckDuckGo search + optional page scraping (`/v1/search` endpoint) | Python |
| elasticsearch | Vector store & knowledge base | Elasticsearch 9.1.4 |
| kibana | Optional UI for Elasticsearch | Kibana 9.1.4 |

## Repository Layout
```
services/
  backend/
  frontend/
  rag-orchestrator/
  search-agent/
  llm-engine/
  embedding-worker/
infrastructure/
  elasticsearch/
  kibana/
scripts/
```

Refer to `rollout.md` for the chronological implementation plan and to `AGENTS.md` for operating notes and guardrails.

## Next Steps
- Fill in Dockerfiles and service bootstraps per rollout steps.
- Implement automated tests mapped to `make test`.
- Document model download and caching workflow once services are in place.

To bootstrap Elasticsearch templates after the cluster is running, execute `make bootstrap-es`.

## Elasticsearch Bootstrap
Once Elasticsearch is running, execute `make bootstrap-es` to apply index templates and create base indices.
