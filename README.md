# Teacher App Scaffold

This repository hosts a containerized learning companion that guides users through custom training paths using Retrieval-Augmented Generation (RAG) backed by Elasticsearch. The stack comprises a Vue 3 SPA, Laravel 12 API, and Python microservices coordinating local LLM + embedding models that run comfortably on an AMD Ryzen 5 7600 / Radeon RX 6600 workstation.

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
The host already loads the `amdgpu` kernel driver, and `lspci` identifies a Radeon RX 6600 (Navi 23). No ROCm userland packages are installed yet, so use the following Ubuntu 24.04 guidance when you want GPU acceleration.

### Verify the GPU stack
```bash
lspci -nn | grep -E "VGA|Display"  # should list the Radeon RX 6600 (gfx1032)
lsmod | grep amdgpu                       # confirm the kernel module is loaded
sudo dmesg | grep -i amdgpu | tail -20    # inspect recent driver messages
```

### Check for existing ROCm packages
```bash
dpkg -l | grep -i rocm
which rocminfo && rocminfo | head
which hipcc && hipcc --version
```
If these commands report nothing, ROCm userland components are not yet present.

### Install/upgrade ROCm 5.7.0 (Ubuntu 24.04 example)
ROCm 5.7 officially supports the RX 6600. Confirm the available release string first, then install:
```bash
# Discover ROCm versions published in the configured repository
apt-cache policy rocm-libs | head

# Refresh AMD + Ubuntu repositories
sudo apt update

# Install ROCm runtime and HIP without re-installing kernel DKMS modules
sudo amdgpu-install --usecase=rocm,hip -y --no-dkms --rocmrelease=5.7.0 --accept-eula

# Optional diagnostics tools
sudo apt install rocminfo rocm-hip-runtime-dev rocm-smi librocm-smi64-1

# Allow your user (and Docker) to access GPU device nodes
sudo usermod -a -G video,render $USER
newgrp video   # reload video group without full relog
newgrp render  # load render group (or log out/in)
```
If `rocminfo` still reports `/dev/kfd` permission errors, run `groups` to confirm membership and log out/in if necessary.

Adjust `--rocmrelease` to match the `apt-cache` candidate and consult AMD's compatibility matrix if you change GPUs.

### Post-install validation
```bash
rocminfo | less   # expect gfx1032 for an RX 6600
rocm-smi          # temperature, clocks, fan speed
hipcc --version   # confirms HIP toolchain availability
```
If these binaries are not in your PATH, check `/opt/rocm-*/bin` for the versioned symlinks installed by `amdgpu-install`.
The commands should succeed and report ROCM 5.7.0 (or newer) with the RX 6600 detected; `hipcc --version` prints warnings that can be ignored.

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
