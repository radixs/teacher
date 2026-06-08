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

## Rag-Orchestrator Code Style
- One class per file in `services/rag-orchestrator/app` unless a file is a deliberate package helper such as `__init__.py`.
- File names must describe responsibility explicitly: use suffixes such as `_client`, `_repository`, `_router`, `_mapper`, `_request_dto`, `_response_dto`, and `_service` where they are part of the established naming.
- DTOs live in `app/dto/`; internal persistent/domain structures live in `app/models/`.
- Response/document shaping belongs in `app/mappers/`, not in routers or repositories.
- Avoid generic local names such as `payload`, `data`, `dict`, or `string` when the business meaning is known.
- Prefer passing full `SessionModel` objects through workflow/service layers; keep id-only lookup methods narrow.
- Do not introduce silent fallback behavior in rag-orchestrator. If LLM, embedding, search, grading, or startup prerequisites fail, raise explicit errors and surface them clearly.

## Current Skeleton Status
- The main end-to-end learning flow is active across backend, rag-orchestrator, llm-engine, embedding-worker, search-agent, and Elasticsearch.
- Rag-orchestrator now uses DTOs, mappers, repositories, explicit bootstrap/container wiring, and one-class-per-file service modules.
- Strict failure behavior is enabled in rag-orchestrator: calibration generation, roadmap generation, search, embeddings, grading, and startup hydration now fail loudly instead of degrading silently.
- `make test` currently passes across backend, rag-orchestrator, search-agent, and frontend build smoke. One known warning remains from `httpx` test-client deprecation in rag-orchestrator tests.

## Next Conversation Reminders
- On new sessions, rerun `make test` first to confirm the refactor baseline is still green before starting the next implementation phase.
- `rag-orchestrator_flows.md` is now the canonical current flow map for the Python orchestrator; prefer updating it over older narrative docs when flow behavior changes.
- If touching rag-orchestrator tests, keep an eye on the remaining `httpx` test-client deprecation warning.
- GPU path is containerised ROCm only (`/dev/kfd`, `/dev/dri`, user in video/render). Avoid host ROCm installs.
