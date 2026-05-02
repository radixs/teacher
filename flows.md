# Service Interaction Flows

This document maps the runtime interactions between the containers that compose the Teacher learning mentor and highlights the key Retrieval-Augmented Generation (RAG) and semantic search concepts they rely on.

## 1. User Session Lifecycles

### 1.1 Calibration (session bootstrap)
1. `frontend` collects learner answers via the Vue UI and POSTs them to `backend` (Laravel API).
2. `backend` persists raw responses and metadata into Elasticsearch indices (`session_interactions`, `user_profiles`).
3. `backend` requests a calibration prompt from `rag-orchestrator` (`/v1/sessions`).
4. `rag-orchestrator` enriches the request by:
   - Pulling prior insights from Elasticsearch (`knowledge_snapshots`, `dependency_graph`).
   - Building semantic context blocks (previous answers, prerequisite graph edges).
   - Forwarding the assembled prompt to `llm-engine` for natural language generation.
5. `llm-engine` (llama.cpp + `mistral-7b-instruct` weights) returns the next calibration turn.
6. `rag-orchestrator` stores the generated turn in Elasticsearch and responds to `backend`.
7. `backend` relays the turn to `frontend` and updates session state for follow-up questions.

### 1.2 Tuning (roadmap planning)
1. Once calibration completes, `frontend` triggers roadmap generation via `backend`.
2. `backend` calls `rag-orchestrator` (`/v1/roadmap`) with calibration insights.
3. `rag-orchestrator` fetches relevant prerequisite links from Elasticsearch (`dependency_graph`).
4. For missing context, it may invoke `search-agent` to pull supplemental material (DuckDuckGo HTML + scraping).
5. `rag-orchestrator` consolidates retrieved knowledge and submits a roadmap prompt to `llm-engine`.
6. Generated roadmap entries are embedded by `embedding-worker` and indexed into Elasticsearch (`learning_resources`).
7. `backend` returns the structured roadmap to `frontend` for visualization.

### 1.3 Learning Loop (per concept)
1. Learner actions (viewing resources, submitting exercises) flow from `frontend` to `backend`.
2. For each learner question or exercise submission, `backend` calls `rag-orchestrator` (`/v1/assist` or `/v1/grade`).
3. `rag-orchestrator` performs semantic retrieval:
   - Queries Elasticsearch vector store using `embedding-worker` vectors.
   - Merges lexical (BM25) and vector matches into a ranked context bundle.
4. Context and learner inputs feed the prompt sent to `llm-engine`.
5. Responses (hints, explanations, or evaluations) are stored in Elasticsearch (`session_interactions`, `knowledge_snapshots`).
6. Grading flows additionally apply `grading_profiles.yaml` templates to structure evaluation JSON before returning to `backend`.

## 2. Supporting Data Flows

### 2.1 Embedding Generation
- `rag-orchestrator` requests embeddings from `embedding-worker` when new documents, roadmap nodes, or learner submissions need vector representations.
- `embedding-worker` (sentence-transformers + `bge-base-en-v1.5`) caches the model on disk and returns 768-d floating-point vectors.
- `rag-orchestrator` writes embeddings alongside metadata into Elasticsearch vector fields.

### 2.2 External Search Augmentation
- `rag-orchestrator` calls `search-agent` when internal knowledge is insufficient or freshness is required.
- `search-agent` fetches DuckDuckGo HTML, extracts organic results, and optionally scrapes pages (respecting robots and backoff rules).
- Cleaned snippets are embedded, scored, and optionally indexed for reuse.

### 2.3 Model Serving + Acceleration
- `llm-engine` loads `mistral-7b-instruct` via llama.cpp with CPU execution by default (`gpu_layers=0`).
- If HIP acceleration is enabled later, `llm-engine` consumes ROCm device mounts (`/dev/kfd`, `/dev/dri`) provided by Docker Compose.
- Prompt/response traffic between `rag-orchestrator` and `llm-engine` is JSON over HTTP, with stream support planned.

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
