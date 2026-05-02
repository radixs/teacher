# Teacher App Scaffold

This repository hosts a containerized learning companion that guides users through custom training paths using Retrieval-Augmented Generation (RAG) backed by Elasticsearch. The stack comprises a Vue 3 SPA, Laravel 12 API, and Python microservices coordinating local LLM + embedding models that run comfortably on an AMD Ryzen 5 7600 / Radeon RX 6600 workstation.

## Explanation for Dummies.

xxxx
plan

sections description - what to expect today
what is rag
- poll 1-10 what do you know about it
how it works based on child example - knowledgeable low iq librarian
- questions - some portal users can log into and give their answers
- what will happen when librarian does not use RAG
- what will happen when librarian uses RAG
how it works based on this app - show around
- develop a story with session start and end, some user inputs
behind the scenes - explain components
- add a logging that displays what is done in a file
- how storing to rag works
- how rag retrieval works
- dimensions and vectors (weights)
- the whole process flow, models, python scripts, laravel app
- make a flow chart, after passing each section add to the flow simple summary to previous steps
- quiz
possible uses in auto1
- having RAG up to date - need to listen to everything, but at least does not require documentation updates and model retrain. Does not hallucinate but need proper tagging (cross service flows)
- coding in Claude Code
- ticket making (JIRA append)
- documentation making (autocomplete)
- log search
aws service requirements, mcp
- models - host or use external
- rollout plan
cag
- what is it and how it is different
- is it more useful

xxxx


## Status
Calibration flow implemented: sessions begin with guided questions whose answers are stored in Elasticsearch for later tuning.
Tuning roadmap generator creates a dependency list after calibration and stores it in Elasticsearch.
Learning phase scaffolding: each concept exposes resources + exercises and advances when answers meet placeholder evaluation (full grading arrives in Step 13).
The project is in the bootstrap phase. Core services, orchestration scripts, and documentation are being scaffolded according to the rollout plan in `rollout.md`.

## Prerequisites

## Quick Start
1. `cp .env.dist .env` and tweak ports/paths as desired.
2. Download or cache models ahead of time if needed; otherwise the first `make up` will fetch them.
3. Run `make build` to build all images (optional, compose will auto-build).
4. Start the stack with `make up`; Vue frontend is on `http://localhost:${FRONTEND_PORT:-3000}` and Laravel API on `http://localhost:${BACKEND_PORT:-8080}`.
5. Apply Elasticsearch templates once the cluster is up: `make bootstrap-es`.
6. Run `make test` to execute backend/Python unit suites and a frontend build smoke.
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

## Services
- Kibana: http://localhost:5601 (dashboard + index inspection)


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

## Grading Configuration
- Modify `services/rag-orchestrator/config/grading_profiles.yaml` to tweak rubric weights, thresholds, and feedback messaging.
- Set `RAG_GRADING_PROFILE` in `.env` to switch between profiles.

## Lab Primers
- Request a lab skeleton in chat with `/lab <concept>` (concept optional; defaults to current learning concept).
- The response includes docker-compose, Makefile, README, and notes. Copy them into a directory or enable auto-generation by setting `RAG_LAB_AUTO_WRITE=1` and `RAG_LAB_OUTPUT_ROOT=/tmp/labs`.


## GPU Acceleration (AMD ROCm)
> ⚠️ **Heads up:** Installing ROCm directly on the host can replace the stock Mesa/AMDGPU stack. On this machine it swapped the RX 6600 driver for an Aldebaran server stack until ROCm was fully removed. If you rely on the desktop driver, prefer containerised ROCm instead of host-level packages.

### Safer approach: ROCm inside Docker/Podman
1. Install AMD’s out-of-tree repackaged runtime inside the container image (as `llm-engine` already does via the `rocm/dev-ubuntu` base image).
2. Map the GPU device nodes when launching services:
   ```yaml
   devices:
     - /dev/kfd:/dev/kfd
     - /dev/dri:/dev/dri
   group_add:
     - video
   ```
3. Keep the host on the standard Mesa/AMDGPU driver; only the container pulls in ROCm libraries.
4. When upgrading ROCm, rebuild the `llm-engine` image so it links against the new runtime.

### Optional host-side checks (no ROCm install required)
```bash
lspci -nn | grep -E "VGA|Display"   # verify the GPU is the Radeon RX 6600 (gfx1032)
lsmod | grep amdgpu                  # confirm the kernel module is loaded
```

If you still want to attempt a host installation, be aware it may alter the system driver. Back up, and only proceed if you are prepared to roll back. The previous step-by-step host install commands have been intentionally removed to avoid accidental driver replacement.
### Docker integration checklist (step-by-step)
1. **Expose GPU device files** – in `docker-compose.yml`, ensure the `llm-engine` service contains:
   ```yaml
   devices:
     - /dev/kfd:/dev/kfd
     - /dev/dri:/dev/dri
   group_add:
     - video
   ```
   This gives the container access to the GPU driver nodes.
2. **Allow Docker to access the GPU** – add your user to the `video` and `render` groups so containers inherit the permissions:
   ```bash
   sudo usermod -a -G video,render $USER
   newgrp video
   newgrp render
   ```
   If you have customised Docker to run as a non-root user, identify it with `ps aux | grep dockerd` and add that account too; by default Docker runs as `root` so no extra step is needed. Logging out/back in achieves the same effect.
3. **Set the correct GFX override** – if `rocminfo` shows a different GFX code, update `.env` and compose:
   ```bash
   echo HSA_OVERRIDE_GFX_VERSION=gfx1032 >> .env
   ```
   Then reference `$HSA_OVERRIDE_GFX_VERSION` under the `environment:` section of `llm-engine` in `docker-compose.yml`.
4. **Rebuild after ROCm updates** – whenever ROCm packages change on the host, rebuild the image so it links against the matching runtime:
   ```bash
   docker compose build llm-engine
   docker compose up -d llm-engine
   ```
