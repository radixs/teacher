# AGENT OPERATING NOTES

## Mission Context
- Project goal: interactive learning mentor with RAG over Elasticsearch, delivered via Vue 3 SPA + Laravel 12 backend + Python RAG services.
- Hardware target: AMD Ryzen 5 7600 CPU, Radeon RX 6600 GPU, 32 GB RAM; ensure models run within these limits.
- All services containerized; host machine must remain untouched beyond Docker usage.

## Canonical Architecture Snapshot
- Core services: `frontend` (Vue/Vite), `backend` (Laravel 12), `rag-orchestrator` (FastAPI), `llm-engine` (llama.cpp), `embedding-worker` (sentence-transformers), `search-agent` (DuckDuckGo + scraping), `elasticsearch` (9.1.4), optional `kibana`.
- Models: chat → `mistral-7b-instruct-v0.2` (Q4_K_M); embeddings → `bge-base-en-v1.5` (768 dims).
- `llm-engine`: defaults to HIP GPU inference on the RX 6600 (`LLM_ACCELERATION_MODE=gpu`, `gpu_layers=32`). Set `LLM_ACCELERATION_MODE=cpu` to force CPU fallback.
- ES indices: `user_profiles`, `knowledge_snapshots`, `learning_resources`, `dependency_graph`, `session_interactions`.

## RAG & Interaction Rules
- Maintain stateless conversational context: persist prior turns + insights in Elasticsearch; fetch via semantic search per prompt.
- Enforce calibration → tuning → learning workflow. `/no more` triggers summary + persistence.
- Exercise grading executed through LLM evaluation prompts guided by `grading_profiles.yaml`.
- Lab provisioning: respond with docker-compose + Makefile recipes; only create files under allowed temp paths if explicitly instructed.

## Environment Handling
- Credentials live in `.env`; provide `.env.dist` defaults only.
- Web search limited to DuckDuckGo HTML endpoint with polite scraping (user-agent rotation, backoff, robots compliance).
- No paid APIs; no direct Google scraping.
- Ensure Docker Compose orchestrates complete stack; Makefile commands wrap common workflows.

## Rollout.md Protocol
- Before starting a new step, confirm whether the user wants to commit current changes.
- When a step is completed: update `rollout.md` status to `completed` and briefly note accomplishments.
- If interrupted, resume from the last incomplete step referencing notes column.

## Testing Strategy Reminders
- `make test` beats: container health checks, Laravel API tests (WireMock stubs), RAG integration against ephemeral ES, Vue UI e2e with mocked backend.
- Prefer stubbed dependencies over hitting live services during automated tests.

## Change Safety Checklist
- Never alter host machine configuration without explicit approval.
- Avoid deleting or overriding user-created files unless part of agreed plan.
- Work in ASCII unless file already uses Unicode.

## Session Resilience
- User’s OpenAI Plus plan may interrupt long sessions; keep actionable notes in `rollout.md` and this file so progress is easy to resume.
- Grading config lives at `services/rag-orchestrator/config/grading_profiles.yaml`; ensure prompts demand JSON with passed/score/feedback/highlights.
- Lab primers: trigger with `/lab <topic>`; auto-write to `RAG_LAB_OUTPUT_ROOT` when `RAG_LAB_AUTO_WRITE=1`.
- `make test` runs: backend `php artisan test`, rag-orchestrator + search-agent `pytest`, frontend build smoke; extend as stack evolves.
- GPU usage: llama.cpp built with HIP; containers map `/dev/kfd` and `/dev/dri` and expect ROCm drivers. Set `HIP_VISIBLE_DEVICES=-1` to force CPU fallback.
- GPU acceleration: prefer containerised ROCm (see README). Avoid host-level ROCm installs unless you are ready to restore Mesa/AMDGPU.

## Current Skeleton Status
- Project remains at scaffolding stage: backend/frontend/RAG services exist but most behaviour is stubbed.
- Docker compose brings up eight services; containers start but end-to-end flows (RAG orchestration, embedding, grading) still need validation.
- `make test` currently passes Laravel suite but rag-orchestrator pytest fails (422 due to request schema).

## Next Conversation Reminders
- On new sessions, rebuild containers and rerun `make test` to confirm current failures.
- Fix focus: rag-orchestrator POST `/v1/sessions` should accept plain JSON body; adjust FastAPI endpoint and tests.
- Ensure grading config + lab primer dependencies still resolvable.
- GPU path is containerised ROCm only (`/dev/kfd`, `/dev/dri`, user in video/render). Avoid host ROCm installs.
