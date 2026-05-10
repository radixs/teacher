# Teacher App Scaffold

This repository hosts a containerized learning companion that guides users through custom training paths using Retrieval-Augmented Generation (RAG) backed by Elasticsearch. The stack comprises a Vue 3 SPA, Laravel 12 API, and Python microservices coordinating local LLM + embedding models that run comfortably on an AMD Ryzen 5 7600 / Radeon RX 6600 workstation.

## Flow Documentation
- High-level runtime map: `flows.md`
- Gradual beginner-to-technical walkthrough: `detailed_flow_for_dummies.md`
- Manual verification runbook: `manual_tests.md`
- Browser-visible live event stream: `Live Flow Console` at the bottom of the chat view
- Demo-friendly end-to-end trace file: `infrastructure/demo-logs/teacher-flow.log`

## Status
Calibration flow is active: session startup generates personalized calibration questions through the local LLM, with deterministic fallback questions if the model output is unusable.
Tuning roadmap generation is active: calibration answers are combined with fast DuckDuckGo result cards, external resources are embedded and stored in Elasticsearch, and the local LLM produces the roadmap with fallback logic if needed.
Learning phase is active: each concept exposes resources + exercises, grading requests structured JSON from the local LLM, and heuristic grading remains only as a safety net.
`llm-engine` is configured for HIP offload on the target RX 6600 by default (`LLM_ACCELERATION_MODE=gpu`, `LLM_GPU_LAYERS=32`). CPU fallback is a one-line `.env` change: set `LLM_ACCELERATION_MODE=cpu` and restart the stack.
The stack is still a scaffolded project, but the end-to-end learning path now exercises the intended containers instead of placeholder-only logic. Progress remains tracked in `rollout.md`.

## Prerequisites

## Quick Start
1. `cp .env.dist .env` and tweak ports/paths as desired.
2. Download or cache models ahead of time if needed; otherwise the first startup may fetch models or build missing images.
3. Run `make build` to build all images manually if you want to prebuild ahead of time.
4. Start the stack with `make up`; it starts containers from the currently available images and does not force a rebuild. Vue frontend is on `http://localhost:${FRONTEND_PORT:-3000}` and Laravel API on `http://localhost:${BACKEND_PORT:-8080}`.
5. If you changed image-baked files such as Dockerfiles, entrypoints, or non-mounted service code, run `make rebuild` or `make build && make restart`.
6. Apply Elasticsearch templates once the cluster is up: `make bootstrap-es`.
   If bootstrap reports that an index "exists but has no mapped properties", that index was created by an older broken template run. Delete the affected app indices or reset the ES volume, then rerun `make bootstrap-es`.
7. Run `make test` to execute backend/Python unit suites and a frontend build smoke.
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
- `make up` – start the full stack in detached mode using existing images.
- `make rebuild` – rebuild changed images and start the stack.
- `make down` – stop and remove containers.
- `make restart` – restart the stack using existing images.
- `make restart-build` – restart the stack and rebuild changed images.
- `make logs` – follow logs from all services.
- `make test` – execute backend Laravel tests, Python service tests, and a frontend build smoke check.

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
- Add deeper semantic retrieval over stored `learning_resources`, `knowledge_snapshots`, and `user_profiles`.
- Add citation-aware answer generation so the UI can show exactly which stored resources informed a response.
- Add streaming assistant responses from `llm-engine` to the frontend.

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
1. Install AMD’s out-of-tree repackaged runtime inside the container image.
   This project now builds `llm-engine` on `rocm/dev-ubuntu-22.04:6.1.2`, which satisfies the current `llama.cpp` HIP backend requirement.
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
lspci -nn | grep -E "VGA|Display"   # verify the GPU is the Radeon RX 6600
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
   echo HSA_OVERRIDE_GFX_VERSION=10.3.0 >> .env
   ```
   Then reference `$HSA_OVERRIDE_GFX_VERSION` under the `environment:` section of `llm-engine` in `docker-compose.yml`.
4. **Rebuild after ROCm updates** – whenever ROCm packages change on the host, rebuild the image so it links against the matching runtime:
   ```bash
   docker compose build llm-engine
   docker compose up -d llm-engine
   ```

### Live verification markers
After `make restart`, confirm GPU offload with:

```bash
docker compose logs --tail=200 llm-engine
```

Healthy GPU-backed startup should include lines like:

- `ggml_cuda_init: found 1 ROCm devices`
- `Device 0: AMD Radeon RX 6600`
- `load_tensors: offloaded 32/33 layers to GPU`
- `ROCm0 model buffer size`

### Quick mode switch
Use `.env` for the high-level switch:

```bash
LLM_ACCELERATION_MODE=gpu
```

or:

```bash
LLM_ACCELERATION_MODE=cpu
```

Then apply it with:

```bash
make restart
```

Implementation detail:

- `LLM_ACCELERATION_MODE=gpu` keeps `LLM_GPU_LAYERS=32`
- `LLM_ACCELERATION_MODE=cpu` forces `gpu_layers=0` and `HIP_VISIBLE_DEVICES=-1` inside the container entrypoint
