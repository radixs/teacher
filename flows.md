# Service Interaction Flows

This document maps the runtime interactions between the containers that compose the Teacher learning mentor and highlights the key Retrieval-Augmented Generation (RAG) and semantic search concepts they rely on.

## 1. User Session Lifecycles

### 1.1 Calibration (session bootstrap)
1. `frontend` collects learner answers via the Vue UI and POSTs them to `backend` (Laravel API).
2. `backend` forwards the start request to `rag-orchestrator` (`POST /v1/sessions`).
3. `rag-orchestrator` asks `llm-engine` to generate a personalized set of calibration questions using the learner goal + optional profile summary.
4. If the LLM output is missing or invalid, `rag-orchestrator` falls back to a deterministic default question set.
5. `rag-orchestrator` stores the learner profile embedding in Elasticsearch (`user_profiles`) and stores the first assistant calibration turn in `session_interactions`.
6. `rag-orchestrator` persists the full session document in Elasticsearch (`sessions`) and responds to `backend`.
7. `backend` relays the initialized session to `frontend`, which stores it locally for resume.

### 1.2 Tuning (roadmap planning)
1. Once the final calibration answer arrives, the normal `POST /v1/sessions/{session_id}` flow stays inside `rag-orchestrator`; there is no separate `/v1/roadmap` endpoint.
2. `rag-orchestrator` builds a focused search query and calls `search-agent` (`GET /v1/search` with enrichment disabled on the learner-facing hot path).
3. `search-agent` retrieves DuckDuckGo result cards quickly; optional page scraping still exists in the service, but it is not used in the synchronous roadmap request because that added too much latency.
4. `rag-orchestrator` embeds the retrieved resources via `embedding-worker` and stores them in Elasticsearch (`learning_resources`).
5. `rag-orchestrator` sends calibration history + external resources to `llm-engine` and asks it for a structured roadmap JSON document.
6. If the LLM output is unusable, `rag-orchestrator` falls back to an adaptive seed curriculum defined in `services/rag-orchestrator/app/services/tuning.py`.
7. Final roadmap nodes are stored in Elasticsearch (`dependency_graph`), their resources are stored in `learning_resources`, and the first learning concept is returned to the learner.

### 1.3 Learning Loop (per concept)
1. Learner actions (viewing resources, submitting exercises) flow from `frontend` to `backend`.
2. For each learner exercise submission, `backend` calls `rag-orchestrator` through `POST /v1/sessions/{session_id}`.
3. `rag-orchestrator` identifies the current roadmap concept and builds a grading prompt from:
   - concept summary
   - concept resources
   - exercise text
   - rubric from `grading_profiles.yaml`
   - learner answer
4. `llm-engine` receives the grading request through its OpenAI-compatible chat-completions endpoint first, with legacy `/completion` fallback for compatibility.
5. If the model returns valid JSON, `ExerciseGrader` uses that result directly. If the model fails or returns invalid output, the local heuristic fallback is used to avoid blocking the session.
6. Outcomes and assistant feedback are stored in Elasticsearch (`session_interactions`, `knowledge_snapshots`, `sessions`) before being returned to `backend`.

## 2. Supporting Data Flows

### 2.1 Embedding Generation
- `rag-orchestrator` requests embeddings from `embedding-worker` when new documents, roadmap nodes, or learner submissions need vector representations.
- `embedding-worker` (sentence-transformers + `bge-base-en-v1.5`) caches the model on disk and returns 768-d floating-point vectors.
- `rag-orchestrator` writes embeddings alongside metadata into Elasticsearch vector fields.

### 2.2 External Search Augmentation
- `rag-orchestrator` calls `search-agent` during roadmap generation to gather current public learning resources.
- `search-agent` fetches DuckDuckGo HTML, extracts organic results, and returns titles, URLs, and snippets for the hot path.
- Optional page scraping still exists behind `enrich=true`, but it is now treated as a slower operator capability rather than part of the main learner request.
- Retrieved snippets are embedded and indexed into Elasticsearch (`learning_resources`) for reuse during later roadmap and lesson work.

### 2.3 Model Serving + Acceleration
- `llm-engine` loads `mistral-7b-instruct` via llama.cpp with HIP layer offload enabled for the target RX 6600 (`LLM_ACCELERATION_MODE=gpu`, `LLM_GPU_LAYERS=32` by default).
- `llm-engine` consumes ROCm device mounts (`/dev/kfd`, `/dev/dri`) provided by Docker Compose; CPU fallback remains available through a single `.env` switch: `LLM_ACCELERATION_MODE=cpu`.
- Prompt/response traffic between `rag-orchestrator` and `llm-engine` is JSON over HTTP. `rag-orchestrator` prefers `/v1/chat/completions` and falls back to `/completion` when needed.

### 2.4 Observability and Inspection
- `backend`, `rag-orchestrator`, and other services log to stdout; `make logs` aggregates container output.
- Elasticsearch stores structured session history, enabling queries via Kibana dashboards.
- `rollout.md` tracks implementation milestones; update it after completing roadmap tasks.

## 3. Container Responsibilities and Interfaces

| Service | Depends On | Consumes | Publishes |
| --- | --- | --- | --- |
| frontend | backend | REST APIs, WebSockets (planned) | User events → backend |
| backend | rag-orchestrator, elasticsearch | Session APIs, ES indices | Session state, user insights |
| rag-orchestrator | llm-engine, embedding-worker, search-agent, elasticsearch | Prompt templates, embeddings, search results | Generated prompts/responses, ES updates |
| llm-engine | (optional ROCm devices) | Prompt payloads | Model completions |
| embedding-worker | sentence-transformers cache | Text chunks | Embedding vectors |
| search-agent | DuckDuckGo HTML endpoint | Query text | Ranked search snippets |
| elasticsearch | persistent volumes | Index writes (JSON docs, vectors) | Semantic retrieval results |
| kibana | elasticsearch | ES cluster data | Dashboards/visuals |

## 4. Term Glossary (AI & Semantic Search)

- **Retrieval-Augmented Generation (RAG)**: Architecture where an LLM receives retrieved context from a knowledge base to ground responses.
- **Embedding**: Numeric representation of text where semantic similarity is captured as vector distance.
- **Vector Store**: Database (here, Elasticsearch) optimized to index and search high-dimensional embeddings.
- **BM25**: Probabilistic text ranking algorithm combining term frequency and inverse document frequency for lexical search.
- **Semantic Search**: Retrieval technique that matches user intent using embeddings rather than exact keyword overlap.
- **Calibration**: Initial dialogue phase that assesses learner profile and goals to seed personalization.
- **Tuning Roadmap**: Sequenced plan of concepts and resources derived from calibration insights.
- **Context Window**: Portion of retrieved knowledge concatenated with the prompt and sent to the LLM.
- **Grading Profile**: Prompt template specifying evaluation rubric weights, ensuring consistent JSON feedback from the LLM.
- **HIP Acceleration**: AMD’s ROCm runtime path that offloads inference to the Radeon GPU when enabled in `llm-engine`.

## 5. Future Enhancements

- Add streaming responses from `llm-engine` to support token-by-token UI updates.
- Extend `rag-orchestrator` with citation tracking, linking generated answers back to Elasticsearch documents.
- Introduce background jobs for scheduled re-embedding of stale resources and dependency graphs.
