# Detailed Flow For Dummies

This document starts with a simple library story and then gradually moves into exact technical behavior, file ownership, container boundaries, and the current implementation reality of this project.

It is written for experienced backend developers who know distributed application structure, HTTP APIs, persistence, and Docker, but do not yet have intuition for RAG, embeddings, or LLM-driven flows.

## 1. Key Terms First

These terms appear many times in the rest of the document. Each term has two explanations:

- Library picture: the mental image.
- Technical meaning: the real implementation idea.

### Retrieval-Augmented Generation (RAG)

- Library picture: before Louis the expert librarian answers a visitor, other librarians first bring him the most relevant books, notes, and past visit cards. Louis answers using those materials instead of guessing from memory alone.
- Technical meaning: an LLM response is improved by retrieving context from storage first, then placing that context into the prompt. In this project, Elasticsearch is the storage layer and the `rag-orchestrator` decides what context to send with the prompt.

### Embedding

- Library picture: Emily turns each page, question, or learner answer into a secret "shape of meaning" card. Two texts that mean similar things get cards with similar shapes.
- Technical meaning: an embedding is a numeric vector representation of text. Similar meanings produce vectors that are closer together in vector space. This project uses `bge-base-en-v1.5` with 768 dimensions.

### Vector Store and Matrices

- Library picture: instead of storing only words on cards, the library also stores long rows of numeric weights that describe meaning. When a new question arrives, the library compares its weights to old weights and finds the closest matches.
- Technical meaning: a vector store is a database that indexes high-dimensional numeric arrays for nearest-neighbor search. Elasticsearch stores these arrays in `dense_vector` fields. When people casually say "matrices" here, think "organized tables of weights used to compare meaning."

### BM25

- Library picture: one librarian is still very good at old-fashioned keyword lookup. If the visitor says "Elasticsearch relevance tuning," this librarian finds books where those exact words matter a lot.
- Technical meaning: BM25 is a lexical ranking algorithm. It rewards relevant term frequency and discounts overly common terms. It is excellent for exact terms and precise vocabulary.

### Semantic Search

- Library picture: even if the visitor asks "how to make search results feel smarter," the library can still find books about "relevance tuning" because the meaning is close, not just the words.
- Technical meaning: semantic search compares embeddings instead of exact words. It is useful when the wording changes but the intent stays similar.

### Calibration

- Library picture: before teaching starts, the library asks a few warm-up questions to learn what the visitor already knows.
- Technical meaning: this is the first phase of the session. The current code asks the local LLM to generate personalized calibration questions from the learner goal and profile, then falls back to a safe default question set if the model output is unusable.

### Tuning Roadmap

- Library picture: after calibration, the librarians draw a learning map: first shelf A, then shelf B, then shelf C, because some topics unlock later topics.
- Technical meaning: this is the ordered learning plan. The current code combines calibration answers, DuckDuckGo search results, and the local LLM to generate the roadmap, with a deterministic adaptive seed curriculum used only as fallback.

### Context Window

- Library picture: Louis can only keep a limited stack of open notes on his desk at once.
- Technical meaning: the LLM can only process a limited amount of text per request. In `services/llm-engine/config.yaml`, the current context length is `4096`.

### Grading Profile

- Library picture: the librarians use a scoring sheet so every exercise is judged by the same rules instead of mood.
- Technical meaning: `services/rag-orchestrator/config/grading_profiles.yaml` defines the rubric, threshold, and feedback rules used by `ExerciseGrader`.

### HIP Acceleration

- Library picture: Louis can answer using only desk work, or he can ask a very fast helper machine in the back room to speed up heavy thinking.
- Technical meaning: HIP is the AMD ROCm path used by llama.cpp to offload inference work to the Radeon GPU. This project is now configured to offload all 32 Mistral layers by default on the target RX 6600, while CPU fallback remains available through a simple `.env` switch: `LLM_ACCELERATION_MODE=cpu`.

### Dependency Graph

- Library picture: a string map on the wall shows which books must be read before other books make sense.
- Technical meaning: the roadmap is stored as concept nodes with prerequisites. Elasticsearch index `dependency_graph` is used to persist these nodes.

## 2. Reality Check: What Is Real Today vs What Is Still Scaffolded

This project still has scaffolded areas, but the previously missing runtime pieces in the main learning path are now active.

- Calibration is real and now LLM-driven first, with fallback default questions if the model output is invalid.
- Tuning roadmap generation is real and now uses adaptive retrieval: `search-agent` gathers public resources, `embedding-worker` embeds them, Elasticsearch stores them, and `llm-engine` turns that context into a roadmap.
- Learning phase and grading loop are real.
- LLM-based grading now uses the model's chat-completions path first and asks for strict JSON. The heuristic fallback remains only as a safety net when the model response is empty or malformed.
- `search-agent` is now part of the main tuning flow in `app/api/routes/sessions.py`.
- Elasticsearch vector-capable indices `user_profiles` and `learning_resources` are now written on the hot path, not just provisioned.
- Kibana is still only a human inspection screen. That simply means the app does not call Kibana as part of a learner session. A developer or presenter opens Kibana manually in the browser to inspect what Elasticsearch contains.

That distinction still matters. The rest of this document separates:

- implemented hot-path flow
- manual inspection flow
- future enhancement areas

## 3. Shared Building Rules

These files affect multiple librarians at once:

- `docker-compose.yml`
- `.env.dist`
- `README.md`
- `flows.md`
- `rollout.md`
- `AGENTS.md`
- `librarian_story.md`
- `infrastructure/demo-logs/.gitignore`

Important shared runtime choices:

- All services run in Docker containers.
- The main network is `appnet`.
- The chat model is `mistral-7b-instruct-v0.2` in GGUF `Q4_K_M` form.
- Embeddings are `bge-base-en-v1.5`, 768 dimensions.
- Elasticsearch indices are bootstrapped by `infrastructure/elasticsearch/scripts/bootstrap.sh`.
- The single demo log file path is `infrastructure/demo-logs/teacher-flow.log` on the host, mounted into containers as `/shared-logs/teacher-flow.log`.

## 4. Meet The Librarians

Each librarian gets:

- plain child-safe explanation
- exact technical responsibility
- handoff behavior
- owned files and configs

### 4.1 Frontend

#### Child-safe explanation

Frontend is the librarian at the welcome desk. This librarian smiles, asks what the visitor wants to learn, writes down the visitor's replies, shows the conversation on the screen, and hands the request slip to the backend librarian.

Frontend does not decide what to teach. It only collects input, displays output, remembers recent visits in the browser, and sends requests to the next librarian.

#### Technical responsibility

- Vue 3 SPA rendered by Vite.
- Keeps current chat messages, current session id, and browser-local session history in Vuex.
- Calls Laravel API endpoints through Axios.
- Restores the last active session from browser localStorage when the page loads.

#### Handoff behavior

- Hands `goal` and optional `profile` to backend when a new session starts.
- Hands `message` and optional `metadata` to backend for every learner turn.
- Requests session reload by `sessionId` when the user resumes an old session.

#### Files and configs

- `services/frontend/Dockerfile`
- `services/frontend/entrypoint.sh`
- `services/frontend/app/src/main.js`
- `services/frontend/app/src/App.vue`
- `services/frontend/app/src/router/index.js`
- `services/frontend/app/src/store/index.js`
- `services/frontend/app/src/services/api.js`
- `services/frontend/app/src/views/ChatView.vue`
- `services/frontend/app/src/components/ChatInput.vue`
- `services/frontend/app/src/components/ChatMessage.vue`
- `services/frontend/app/src/styles.css`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `FRONTEND_PORT`, `FRONTEND_INTERNAL_PORT`, `FRONTEND_VITE_API_BASE_URL`

### 4.2 Backend

#### Child-safe explanation

Backend is the librarian behind the welcome desk office door. This librarian checks that the request slip is filled correctly, stamps it, and sends it to the smart planning librarian.

Backend is the gatekeeper. It does not invent the lesson content, but it controls the official entrance into the system.

#### Technical responsibility

- Laravel 12 API.
- Defines public REST endpoints for session start, message send, and session load.
- Validates incoming payloads.
- Delegates all session intelligence to `RagClient`, which calls `rag-orchestrator`.
- Emits the first durable log line for each browser action.

#### Handoff behavior

- Receives HTTP from frontend.
- Delegates to `RagClient`.
- Returns JSON payloads back to frontend.

#### Files and configs

- `services/backend/Dockerfile`
- `services/backend/entrypoint.sh`
- `services/backend/app/app/Http/Controllers/Controller.php`
- `services/backend/app/app/Http/Controllers/Api/ChatSessionController.php`
- `services/backend/app/app/Models/User.php`
- `services/backend/app/app/Providers/AppServiceProvider.php`
- `services/backend/app/app/Providers/RagServiceProvider.php`
- `services/backend/app/app/Services/Rag/RagClient.php`
- `services/backend/app/app/Support/FlowLogger.php`
- `services/backend/app/routes/api.php`
- `services/backend/app/routes/web.php`
- `services/backend/app/routes/console.php`
- `services/backend/app/config/app.php`
- `services/backend/app/config/auth.php`
- `services/backend/app/config/cache.php`
- `services/backend/app/config/database.php`
- `services/backend/app/config/filesystems.php`
- `services/backend/app/config/logging.php`
- `services/backend/app/config/mail.php`
- `services/backend/app/config/queue.php`
- `services/backend/app/config/rag.php`
- `services/backend/app/config/services.php`
- `services/backend/app/config/session.php`
- `services/backend/app/storage/logs/.gitignore`
- `services/backend/app/storage/app/.gitignore`
- `services/backend/app/storage/app/public/.gitignore`
- `services/backend/app/storage/app/private/.gitignore`
- `services/backend/app/storage/framework/cache/.gitignore`
- `services/backend/app/storage/framework/cache/data/.gitignore`
- `services/backend/app/storage/framework/sessions/.gitignore`
- `services/backend/app/storage/framework/views/.gitignore`
- `services/backend/app/storage/framework/testing/.gitignore`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `BACKEND_PORT`, `APP_ENV`, `APP_DEBUG`, `RAG_ORCHESTRATOR_URL` via runtime env

### 4.3 RAG Orchestrator

#### Child-safe explanation

This is the head teaching librarian. This librarian decides which stage the visitor is in, asks the next calibration question, builds the learning roadmap, grades exercises, and decides what should happen next.

If frontend is the welcome desk and backend is the gatekeeper, `rag-orchestrator` is the actual brain of the library workflow.

#### Technical responsibility

- FastAPI application under `/v1`.
- Owns the session state machine.
- Persists and restores sessions from Elasticsearch.
- Calls embedding service, search service, and LLM service.
- Generates calibration snapshots, roadmap transitions, learning prompts, and grading actions.

#### Handoff behavior

- Receives validated calls from Laravel backend.
- Calls `embedding-worker` for vectors.
- Calls `llm-engine` for grading prompts.
- Can call `search-agent` for external web retrieval.
- Writes session artifacts to Elasticsearch.

#### Files and configs

- `services/rag-orchestrator/Dockerfile`
- `services/rag-orchestrator/entrypoint.sh`
- `services/rag-orchestrator/requirements.txt`
- `services/rag-orchestrator/app/__init__.py`
- `services/rag-orchestrator/app/main.py`
- `services/rag-orchestrator/app/api/__init__.py`
- `services/rag-orchestrator/app/api/routes/__init__.py`
- `services/rag-orchestrator/app/api/routes/sessions.py`
- `services/rag-orchestrator/app/clients/__init__.py`
- `services/rag-orchestrator/app/clients/elasticsearch.py`
- `services/rag-orchestrator/app/clients/embedding.py`
- `services/rag-orchestrator/app/clients/llm.py`
- `services/rag-orchestrator/app/clients/search.py`
- `services/rag-orchestrator/app/core/__init__.py`
- `services/rag-orchestrator/app/core/config.py`
- `services/rag-orchestrator/app/core/dependencies.py`
- `services/rag-orchestrator/app/core/flow_logger.py`
- `services/rag-orchestrator/app/models/__init__.py`
- `services/rag-orchestrator/app/models/api.py`
- `services/rag-orchestrator/app/models/session.py`
- `services/rag-orchestrator/app/services/__init__.py`
- `services/rag-orchestrator/app/services/calibration.py`
- `services/rag-orchestrator/app/services/grading.py`
- `services/rag-orchestrator/app/services/lab_primer.py`
- `services/rag-orchestrator/app/services/learning.py`
- `services/rag-orchestrator/app/services/session_manager.py`
- `services/rag-orchestrator/app/services/session_store.py`
- `services/rag-orchestrator/app/services/tuning.py`
- `services/rag-orchestrator/app/tests/__init__.py`
- `services/rag-orchestrator/app/tests/test_sessions.py`
- `services/rag-orchestrator/config/grading_profiles.yaml`
- `services/rag-orchestrator/lab_templates/README.md.tpl`
- `services/rag-orchestrator/lab_templates/docker-compose.yml.tpl`
- `services/rag-orchestrator/lab_templates/Makefile.tpl`
- `services/rag-orchestrator/lab_templates/notes.md.tpl`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `RAG_HOST`, `RAG_PORT`, `RAG_RELOAD`, `RAG_LLM_ENGINE_URL`, `RAG_EMBEDDING_SERVICE_URL`, `RAG_SEARCH_AGENT_URL`, `RAG_ELASTICSEARCH_URL`, `RAG_INDEX_*`, `RAG_GRADING_PROFILE`, `RAG_GRADING_CONFIG_PATH`, `RAG_LAB_TEMPLATE_DIR`, `RAG_LAB_OUTPUT_ROOT`, `RAG_LAB_AUTO_WRITE`

### 4.4 LLM Engine (Louis)

#### Child-safe explanation

Louis is the very smart specialist librarian. Louis reads a big stack of notes and tries to produce the final explanation or grading judgment. Louis is smart, but Louis only sees what the other librarians place on the desk.

Louis does not manage the whole library. Louis only answers when asked.

#### Technical responsibility

- Hosts llama.cpp server.
- Loads Mistral 7B Instruct GGUF file.
- Uses CPU by default, with optional HIP/ROCm acceleration later.
- Current hot-path usage is mainly grading via `LlmClient`.

#### Handoff behavior

- Receives HTTP completion requests from `rag-orchestrator`.
- Returns generated text or fails, which triggers fallback behavior upstream.

#### Files and configs

- `services/llm-engine/Dockerfile`
- `services/llm-engine/entrypoint.sh`
- `services/llm-engine/config.yaml`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `LLM_ENGINE_PORT`, `LLM_MODEL_URL`, `LLM_CONTEXT_WINDOW`, `LLM_THREADS`, `LLM_BATCH_SIZE`, `LLM_ACCELERATION_MODE`, `LLM_GPU_LAYERS`, `LLM_SERVER_HOST`, `LLM_SERVER_PORT`, `HSA_OVERRIDE_GFX_VERSION`, `HIP_VISIBLE_DEVICES`

### 4.5 Embedding Worker (Emily)

#### Child-safe explanation

Emily is the librarian who turns text into meaning-shape cards. Emily does not explain anything to the visitor directly. Emily just creates the special number patterns that help the library compare meanings.

#### Technical responsibility

- FastAPI service with sentence-transformers.
- Loads `BAAI/bge-base-en-v1.5`.
- Returns normalized 768-dimensional vectors.

#### Handoff behavior

- Receives text from `rag-orchestrator`.
- Returns embedding vectors.
- Does not persist state itself.

#### Files and configs

- `services/embedding-worker/Dockerfile`
- `services/embedding-worker/entrypoint.sh`
- `services/embedding-worker/requirements.txt`
- `services/embedding-worker/app/__init__.py`
- `services/embedding-worker/app/main.py`
- `services/embedding-worker/app/flow_logger.py`
- `services/embedding-worker/app/tests/test_embed.py`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `EMBEDDING_PORT`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_MODEL_NAME_OR_PATH`, `EMBEDDING_DEVICE`, `EMBEDDING_CACHE_DIR`, `EMBEDDING_DIMENSIONS`

### 4.6 Search Agent

#### Child-safe explanation

This librarian is the one allowed to walk outside your library and check other public libraries. If the home library is missing something, this librarian can bring back book titles, summaries, and sometimes short copied notes.

#### Technical responsibility

- FastAPI service.
- Queries DuckDuckGo HTML endpoint.
- Can optionally fetch and clean result pages for richer content.
- Exists as an external knowledge connector, although it is not yet on the main learner hot path.

#### Handoff behavior

- Receives queries from `rag-orchestrator`.
- Returns result lists and optional enriched page content.

#### Files and configs

- `services/search-agent/Dockerfile`
- `services/search-agent/entrypoint.sh`
- `services/search-agent/requirements.txt`
- `services/search-agent/app/__init__.py`
- `services/search-agent/app/main.py`
- `services/search-agent/app/config.py`
- `services/search-agent/app/flow_logger.py`
- `services/search-agent/app/routes/__init__.py`
- `services/search-agent/app/routes/search.py`
- `services/search-agent/app/clients/__init__.py`
- `services/search-agent/app/clients/duckduckgo.py`
- `services/search-agent/app/scrapers/__init__.py`
- `services/search-agent/app/scrapers/simple.py`
- `services/search-agent/app/tests/__init__.py`
- `services/search-agent/app/tests/test_parse.py`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `SEARCH_AGENT_PORT`, `DUCKDUCKGO_REQUEST_INTERVAL_SECONDS`, `DUCKDUCKGO_USER_AGENT`

### 4.7 Elasticsearch

#### Child-safe explanation

Elasticsearch is the giant catalog room with shelves, card drawers, and special meaning-card cabinets. It remembers sessions, past answers, snapshots, and roadmap nodes so the library does not forget between visits.

#### Technical responsibility

- Stores multiple indices:
  - `sessions`
  - `session_interactions`
  - `knowledge_snapshots`
  - `dependency_graph`
  - `learning_resources`
  - `user_profiles`
- Stores both normal searchable text and vector fields.
- Supports exact lookup, filtered lookup, and semantic-style vector retrieval later.

#### Handoff behavior

- Receives writes from `rag-orchestrator`.
- Can be queried by `rag-orchestrator`.
- Is inspected by humans through Kibana.

#### Files and configs

- `infrastructure/elasticsearch/config/elasticsearch.yml`
- `infrastructure/elasticsearch/config/jvm.options`
- `infrastructure/elasticsearch/config/log4j2.properties`
- `infrastructure/elasticsearch/config/elasticsearch.keystore`
- `infrastructure/elasticsearch/indices/sessions.json`
- `infrastructure/elasticsearch/indices/session_interactions.json`
- `infrastructure/elasticsearch/indices/knowledge_snapshots.json`
- `infrastructure/elasticsearch/indices/dependency_graph.json`
- `infrastructure/elasticsearch/indices/learning_resources.json`
- `infrastructure/elasticsearch/indices/user_profiles.json`
- `infrastructure/elasticsearch/scripts/bootstrap.sh`
- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` values `ELASTICSEARCH_PORT`, `ELASTICSEARCH_TRANSPORT_PORT`, `ELASTICSEARCH_HOST`, `ELASTICSEARCH_USERNAME`, `ELASTICSEARCH_PASSWORD`

### 4.8 Kibana

#### Child-safe explanation

Kibana is the glass observation room. It does not teach the visitor. It lets the adult librarians look through windows and see what is stored in the big catalog room.

#### Technical responsibility

- Browser UI for inspecting Elasticsearch data.
- Useful for validating session state, interactions, snapshots, and dependency graph nodes during demos.

#### Handoff behavior

- Reads from Elasticsearch.
- Does not participate in learner request execution.

#### Files and configs

- Shared config: `docker-compose.yml`
- Shared env: `.env.dist` value `KIBANA_PORT`
- There is no dedicated local `infrastructure/kibana` tree in the current repository snapshot.

## 5. Every Flow In The Project: Technical View + Library Story Overlay

Each flow below has two parts:

- Technical flow: the real call chain.
- Library story: the same event explained with the library picture.

### 5.1 Container Boot Flow

#### Technical flow

1. `docker-compose.yml` starts all services on `appnet`.
2. `backend` runs `services/backend/entrypoint.sh`, ensures Composer dependencies, generates Laravel key, and runs `php artisan serve`.
3. `frontend` runs Vite app container.
4. `rag-orchestrator` boots FastAPI and, on startup, preloads saved sessions by calling `SessionStore.list()`.
5. `llm-engine` runs `services/llm-engine/entrypoint.sh`, resolves config, ensures model file exists, then launches `llama-server`.
6. `embedding-worker` starts FastAPI app and loads the transformer model lazily on first use.
7. `search-agent` starts FastAPI app.
8. `elasticsearch` starts with mounted config and data volume.
9. `kibana` waits on Elasticsearch.

#### Library story

The library building opens. Each librarian walks to the correct desk. Louis checks whether the big reference book is on the shelf. Emily warms up the meaning-card machine. The head librarian checks yesterday's visitor cards and puts them back on the work table.

### 5.2 Elasticsearch Bootstrap Flow

#### Technical flow

1. Operator runs `make bootstrap-es`.
2. `infrastructure/elasticsearch/scripts/bootstrap.sh` applies each template file under `infrastructure/elasticsearch/indices`.
3. The script creates the concrete indices explicitly.

#### Library story

Before visitors arrive, the filing cabinets are labeled and empty drawers are created so every future card has the right home.

### 5.3 Frontend Load And Session Hydration Flow

#### Technical flow

1. `services/frontend/app/src/main.js` dispatches `store.dispatch('hydrateFromStorage')` before mounting the app.
2. `services/frontend/app/src/store/index.js` reads:
   - `teacher.sessionHistory`
   - `teacher.activeSessionId`
3. If `pendingRestoreId` exists, `loadSession(sessionId)` calls `api.fetchSession(sessionId)`.
4. Axios in `src/services/api.js` calls `GET /api/v1/sessions/{sessionId}`.
5. Laravel route `routes/api.php` maps to `ChatSessionController::show`.
6. `RagClient::fetchSession()` calls `GET /v1/sessions/{sessionId}` on `rag-orchestrator`.
7. FastAPI route `get_session()` returns the in-memory session, or restores it from Elasticsearch through `SessionStore.get()` if needed.
8. Response travels back to Vuex and updates UI state.

#### Library story

When the visitor walks back in, the welcome desk checks whether the visitor already has a card in their pocket. If yes, the gatekeeper asks the head librarian to pull the old learning folder back from storage so the conversation can continue from the same page.

### 5.4 Start New Session Flow

#### Technical flow

1. User enters goal and optional profile in `ChatView.vue`.
2. `start()` dispatches `store.dispatch('startSession', { goal, profile })`.
3. Vuex `startSession` calls `api.startSession(payload)`.
4. Axios issues `POST /api/v1/sessions`.
5. Laravel `ChatSessionController::start()` validates:
   - `goal` required string
   - `profile` optional array
6. `RagClient::startSession()` forwards `POST /v1/sessions`.
7. FastAPI `start_session()`:
   - calls `SessionManager.create_session()`
   - creates calibration queue via `CalibrationPlanner.questions()`
   - calls `SessionManager.next_calibration_question()`
   - appends assistant message with the first calibration question
   - stores assistant interaction in Elasticsearch index `session_interactions`
   - stores full session document in Elasticsearch index `sessions`
8. Response returns to Laravel, then to Vuex, which stores:
   - `sessionId`
   - `messages`
   - `phase`
   - `sessionHistory`
9. Frontend writes session history and active session id to localStorage.

#### Library story

The visitor tells the front desk, "I want to learn X." The desk clerk writes the request. The office librarian checks the slip. The head librarian creates a fresh folder, places the first warm-up question inside, files a copy in the archive room, and sends the question back to the visitor.

### 5.5 Calibration Answer Loop

#### Technical flow

1. User sends a message through `ChatInput.vue`.
2. `ChatView.vue` calls `store.dispatch('sendMessage', { message })`.
3. Vuex appends the local user message immediately for responsive UI.
4. Axios calls `POST /api/v1/sessions/{sessionId}`.
5. Laravel `ChatSessionController::message()` validates:
   - `message` required string
   - `metadata` optional array
6. `RagClient::sendMessage()` forwards to FastAPI `send_message()`.
7. `send_message()`:
   - restores session from Elasticsearch if not already in memory
   - appends user message to transcript
   - requests embedding from `embedding-worker`
   - stores user interaction in `session_interactions`
   - records answer in `calibration_history`
   - synthesizes a simple snapshot via `CalibrationPlanner.synthesize_snapshot()`
   - stores snapshot in `knowledge_snapshots`
   - asks `SessionManager.next_calibration_question()`
   - appends the next assistant question
   - stores assistant interaction
   - persists updated session in `sessions`
8. Response returns to Vuex.
9. Vuex appends the assistant message and updates summary state.

#### Library story

The visitor answers a warm-up question. Emily makes a meaning card for the answer. The head librarian puts the answer into the visitor folder, writes a short note about it, files that note, chooses the next question, and sends it back.

### 5.6 Calibration Completion -> Tuning Roadmap -> Learning Intro Flow

#### Technical flow

1. The final calibration answer arrives through the same `send_message()` endpoint.
2. `SessionManager.next_calibration_question()` returns `None`.
3. `TuningProgramGenerator.build_search_query()` derives a search query from the goal and calibration answers.
4. `SearchClient.search(..., enrich=False)` calls `search-agent`.
5. Returned external resources are embedded and written into Elasticsearch `learning_resources`.
6. `TuningProgramGenerator.generate()` sends calibration answers plus retrieved resources to `llm-engine` and expects roadmap JSON back.
7. `SessionManager.set_tuning_plan()` stores the roadmap and sets phase to `tuning`.
8. `SessionManager.begin_learning()` immediately sets phase to `learning`.
9. Each roadmap node is persisted into Elasticsearch `dependency_graph` through `store_dependency_node()`, and concept resources are also persisted to `learning_resources`.
10. `LearningCoordinator.build_overview()` creates the first learning concept summary, resources, and exercise.
11. Assistant message is appended with stage `learning_intro`.
12. Session is persisted to Elasticsearch.

#### Library story

When the warm-up questions are finished, the head librarian first asks the outside-travel librarian for a fast list of useful public references instead of waiting for full photocopies of every page. Then the head librarian uses that quick list plus the visitor folder to draw the learning map, pins it on the wall, marks the first shelf to visit, and gives the first exercise card to the visitor.

### 5.7 Learning Answer -> Pass Path

#### Technical flow

1. Learner submits an answer while `session.phase == "learning"`.
2. `send_message()` identifies current concept via `LearningCoordinator.current_node()`.
3. `ExerciseGrader.evaluate()` builds a grading prompt from:
   - concept metadata
   - resources
   - exercise text
   - rubric from `grading_profiles.yaml`
   - learner answer
4. `LlmClient.generate()` calls `llm-engine`.
5. If the response contains parseable JSON, grading result is used. Otherwise `ExerciseGrader._heuristic_fallback()` computes score locally.
6. If `passed == true`:
   - `SessionManager.record_learning_outcome()` stores concept status `complete`
   - knowledge snapshot is stored in `knowledge_snapshots`
   - `SessionManager.advance_concept()` moves to the next concept
   - next concept overview is generated unless roadmap is finished
7. Assistant response is stored in `session_interactions`.
8. Updated session is saved in `sessions`.

#### Library story

The visitor finishes a lesson and hands in homework. Louis reviews it using the scoring sheet. If the answer is good enough, the head librarian stamps the concept as completed and hands over the next shelf card.

### 5.8 Learning Answer -> Retry Path

#### Technical flow

1. Same grading setup as the pass path.
2. If `passed == false`:
   - `SessionManager.record_learning_outcome()` stores status `needs_revision`
   - snapshot is stored, usually without embedding for failed answer persistence
   - current concept index stays the same
   - assistant message uses stage `learning_retry`
3. Session persists without advancing concept.

#### Library story

The homework is not wrong forever; it is just not ready yet. Louis writes feedback, the head librarian keeps the visitor at the same shelf, and says, "Try again with these corrections."

### 5.9 Full Completion Flow

#### Technical flow

1. Final concept answer passes grading.
2. `SessionManager.advance_concept()` increments beyond last roadmap node.
3. Session phase becomes `learning_complete`.
4. Assistant returns completion message.
5. Subsequent messages go through the `else` branch in `send_message()` and receive:
   - "Learning program already completed. Use /no more to wrap up or ask for a recap."

Important note:

- The message mentions `/no more`, but there is not yet an implemented `/no more` command branch in `sessions.py`.

#### Library story

The visitor has finished every planned shelf. The library marks the folder complete and says the formal wrap-up ritual exists, but in the current building that ritual is not fully built yet.

### 5.10 Resume Existing Session Across Later Visits

#### Technical flow

1. Browser stores `sessionHistory` and active session id in localStorage.
2. Later, the user returns.
3. `hydrateFromStorage()` tries `loadSession()`.
4. Backend and RAG fetch the session from memory or Elasticsearch.
5. UI shows:
   - active goal
   - current phase
   - previous transcript

#### Library story

The visitor leaves the library and comes back another day. The welcome desk recognizes the folder number and brings back the exact same folder instead of starting over.

### 5.11 `/lab` Primer Flow

#### Technical flow

1. User sends a message beginning with `/lab`.
2. `send_message()` detects the command before normal grading flow.
3. Requested concept is resolved from:
   - command argument if present
   - current learning concept if already learning
   - session goal otherwise
4. `LabPrimer.generate()` renders:
   - `README.md`
   - `docker-compose.yml`
   - `Makefile`
   - `notes.md`
5. If `RAG_LAB_AUTO_WRITE=1` and `RAG_LAB_OUTPUT_ROOT` is set, files can be written automatically.
6. Assistant returns the generated file blocks in markdown fences.
7. Interactions and updated session are persisted.

#### Library story

The visitor asks, "Can I get a mini practice kit?" The head librarian assembles a small box with instructions, a room setup card, a task list, and study notes.

### 5.12 LLM Grading Flow

#### Technical flow

1. `ExerciseGrader` builds a prompt with strict JSON output instructions.
2. `LlmClient.generate()` first sends an OpenAI-compatible `POST /v1/chat/completions` request to `llm-engine`, with legacy `/completion` fallback for compatibility.
3. If the model returns valid JSON, `_parse_result()` extracts:
   - `passed`
   - `score`
   - `feedback`
   - `highlights`
4. If parsing or transport fails, heuristic fallback scores by answer length and a few keywords.

Current implementation truth:

- The normal path is now truly model-backed.
- The heuristic path remains as a resilience guard, not as the intended primary grader.

#### Library story

Louis is supposed to judge the homework. If Louis is unavailable, the library uses a simpler emergency checklist so the session can continue.

### 5.13 Search-Agent Flow (Now Part Of The Tuning Hot Path)

#### Technical flow

1. `search-agent` exposes `/v1/search?q=...&enrich=...`.
2. `DuckDuckGoClient.search()` requests the DuckDuckGo HTML endpoint.
3. `parse_results()` extracts result cards.
4. Optional enrichment fetches individual result pages with `WebScraper.fetch()`.
5. `SearchClient` in `rag-orchestrator` calls this service when calibration completes and the roadmap is about to be generated.
6. The current learner-facing hot path calls it with `enrich=False`, so roadmap generation uses result cards and snippets without waiting for page scraping.
7. Normalized search results are embedded and written into Elasticsearch `learning_resources`.
8. The roadmap prompt sent to `llm-engine` includes these retrieved resources.

Current implementation truth:

- `SearchClient` exists and is now part of the active tuning flow.
- The learner-facing roadmap request now uses fast result cards and snippets, not inline page scraping.
- The search results are not just transient. They are persisted for reuse in `learning_resources`.

#### Library story

The outside-travel librarian now leaves the building when the library needs to build the learning map. The returned book cards are copied into the local catalog so they can be reused later.

### 5.14 Elasticsearch Persistence Flow

#### Technical flow

Current hot-path writes:

- `sessions`
  - full session document via `SessionStore.save()`
- `session_interactions`
  - every assistant and user turn via `store_interaction()`
- `knowledge_snapshots`
  - calibration snapshots and learning result summaries
- `dependency_graph`
  - generated roadmap nodes
- `user_profiles`
  - profile summary and profile embedding stored at session start
- `learning_resources`
  - external search results and roadmap resources stored with embeddings during tuning

#### Library story

After almost every meaningful step, the librarians make copies of the important papers and place them in the correct drawers so nothing is lost if someone forgets or leaves.

### 5.15 Kibana Inspection Flow

#### Technical flow

1. A developer, tester, or presenter opens Kibana in the browser by hand.
2. Kibana connects to Elasticsearch.
3. They inspect indices, documents, and timestamps.

Plain-language clarification:

- Kibana is not a service your learner session calls automatically.
- It is a dashboard humans open manually when they want to inspect what Elasticsearch contains.

#### Library story

The head of the library steps into the observation room and looks through the glass at how the filing cabinets are filling up.

### 5.16 Demo Logging Flow

#### Technical flow

1. `docker-compose.yml` mounts `./infrastructure/demo-logs` into owned service containers as `/shared-logs`.
2. Each owned service writes to `FLOW_LOG_PATH`, default `/shared-logs/teacher-flow.log`.
3. Backend logs request entry and upstream delegation.
4. RAG orchestrator logs state transitions, persistence, grading, and service calls.
5. Embedding worker logs vector generation.
6. Search agent logs query and enrichment work.
7. LLM engine logs startup and model-load events, while per-request LLM events are logged by `rag-orchestrator` at the client boundary.

Important design note:

- The frontend does not append directly to the single file, because browser code should not write into a host-mounted server log file.
- Owned services also push each flow event to a backend event stream, and the frontend shows the recent window in the `Live Flow Console` at the bottom of the app.
- Elasticsearch and Kibana are vendor containers. Their participation is logged at the project-owned call boundary rather than by patching the vendor internals.

#### Library story

Every owned librarian writes a short diary line into one shared notebook. Some outside machines do not write directly into that notebook, so the nearby librarian writes, "I just asked that machine to do X" and "it answered with Y."

## 6. Professional-Only Summary As A Multi-Session User Story

This section intentionally drops the child story and uses only professional language.

### Session 1: First Visit And Calibration Start

1. User opens `/`.
2. `services/frontend/app/src/main.js` dispatches `hydrateFromStorage`.
3. No active session is restored, so `ChatView.vue` shows the start form.
4. User enters goal and optional background.
5. `ChatView.vue::start()` dispatches `store.startSession`.
6. `services/frontend/app/src/store/index.js` action `startSession` calls `services/frontend/app/src/services/api.js::startSession`.
7. Axios `POST /api/v1/sessions` reaches Laravel route in `services/backend/app/routes/api.php`.
8. `App\Http\Controllers\Api\ChatSessionController::start()` validates request.
9. `App\Services\Rag\RagClient::startSession()` forwards payload to `rag-orchestrator`.
10. `services/rag-orchestrator/app/api/routes/sessions.py::start_session()` creates session through `SessionManager`.
11. `CalibrationPlanner.questions()` asks `llm-engine` for a personalized question list and falls back to defaults only if needed.
12. `SessionManager.next_calibration_question()` selects first question.
13. Learner profile text is embedded and stored in Elasticsearch `user_profiles`.
14. First assistant message is persisted to `session_interactions`.
15. Full session snapshot is persisted to `sessions`.
16. Response returns to frontend, which stores `sessionId`, `phase`, transcript, and local session history.

### Session 1: Calibration Progress

1. User submits answer through `ChatInput`.
2. Vuex `sendMessage` optimistically appends the user message locally.
3. Backend `ChatSessionController::message()` validates request and forwards it.
4. FastAPI `send_message()` appends user message to transcript.
5. `EmbeddingClient.embed()` calls `embedding-worker /embed`.
6. User interaction with embedding is stored in `session_interactions`.
7. Calibration answer is written into `calibration_history`.
8. Snapshot is synthesized and persisted in `knowledge_snapshots`.
9. Next calibration question is generated from the queue and returned.
10. Session is saved again in `sessions`.

### Session 2: User Returns Later

1. Browser still has `teacher.activeSessionId` and `teacher.sessionHistory`.
2. On page load, Vuex `hydrateFromStorage()` dispatches `loadSession`.
3. Backend `show()` endpoint proxies to `rag-orchestrator`.
4. If the session is not currently in memory, `SessionStore.get()` reads it from Elasticsearch.
5. The user sees the existing transcript and current phase.

### Session 2: Calibration Finishes And Learning Starts

1. Final calibration answer is posted.
2. `send_message()` detects no more calibration questions.
3. `TuningProgramGenerator.build_search_query()` creates an external search query from the goal and calibration answers.
4. `SearchClient.search(..., enrich=False)` calls `search-agent`, which returns normalized public resources.
5. Retrieved resources are embedded and stored in `learning_resources`.
6. `TuningProgramGenerator.generate()` asks `llm-engine` for a structured roadmap using calibration answers plus retrieved resources.
7. `SessionManager.set_tuning_plan()` stores roadmap.
8. `SessionManager.begin_learning()` moves phase to `learning`.
9. Each roadmap node is written to `dependency_graph`, and concept resources are also stored in `learning_resources`.
10. `LearningCoordinator.build_overview()` creates the first concept message.
11. Assistant returns concept summary, resources, and exercise.

### Session 3: First Learning Exercise

1. User studies resources and submits exercise answer.
2. `send_message()` enters the `session.phase == "learning"` branch.
3. Current concept is selected by `LearningCoordinator.current_node()`.
4. `ExerciseGrader.evaluate()` builds prompt using concept and rubric.
5. `LlmClient.generate()` calls `llm-engine` chat-completions first, with legacy completion fallback for compatibility.
6. Result is parsed if valid JSON; otherwise heuristic fallback is used as a safety net.
7. Snapshot of learning outcome is stored in `knowledge_snapshots`.
8. If passed, concept advances; otherwise retry feedback is returned.
9. Assistant response is stored in `session_interactions`.
10. Session is persisted to `sessions`.

### Session 3: Optional Lab Request

1. User sends `/lab vector search`.
2. `send_message()` branches before normal learning evaluation.
3. `LabPrimer.generate()` renders lab files from templates.
4. Assistant returns fenced file content.
5. Session is persisted normally.

### Session 4 And Beyond: Continued Learning Until Completion

1. User repeatedly resumes session from local storage and server state.
2. Each successful answer advances `current_concept_index`.
3. Each failed answer keeps the same index and returns feedback.
4. Once last concept passes, phase becomes `learning_complete`.
5. Session remains loadable through the same resume flow.

## 7. Why The Configuration Looks This Way

These choices are not random. They exist to fit the target machine and the current development stage.

- `mistral-7b-instruct-v0.2` in `Q4_K_M` format: small enough to be practical on the target workstation while still being useful for local experimentation.
- `LLM_ACCELERATION_MODE=gpu` with `gpu_layers=32` by default: the target machine includes an RX 6600, so the project now uses the GPU by default for the chat model while keeping a one-line CPU fallback switch.
- `bge-base-en-v1.5`, 768 dims: well-known embedding model with manageable resource use and direct alignment with the Elasticsearch `dense_vector` mappings.
- Elasticsearch 9.1.4: provides a single place for structured documents and vector-capable fields.
- Laravel in front of FastAPI: keeps a PHP-native public API boundary while isolating RAG logic in Python.
- DuckDuckGo HTML search agent: avoids paid APIs and aligns with the project's operating constraints.
- Session persistence in Elasticsearch: supports stateless container restarts and multi-session resumption.
- Static curriculum roadmap for now: simpler and safer while the surrounding RAG and grading pipeline is still being validated.

## 8. Single Demo Log: What Was Added And How To Use It

### Log file path

- Host path: `infrastructure/demo-logs/teacher-flow.log`
- In-container path: `/shared-logs/teacher-flow.log`

### What writes to it

- Laravel backend:
  - request received
  - request validated
  - upstream RAG dispatch
  - upstream RAG response
- RAG orchestrator:
  - startup hydration
  - session creation
  - message append
  - calibration state changes
  - roadmap creation
  - learning evaluation
  - snapshot and session persistence
  - embedding, search, LLM, and Elasticsearch call boundaries
- Embedding worker:
  - model load
  - embedding request receive
  - embedding completion
- Search agent:
  - startup
  - search request
  - DuckDuckGo request
  - page enrichment
  - response completion
- LLM engine:
  - config load
  - model download
  - server start

### What does not write to it directly

- Frontend browser code
- Elasticsearch internals
- Kibana internals

Those steps are represented by adjacent owned service logs instead.

### Example line format

```text
2026-05-02T16:20:11.123456+00:00 | backend | http.sessions.start.received | Backend received a request from the frontend to start a new learning session. | {"goal_preview":"Learn ESRE fundamentals","has_profile":true}
```

### Suggested demo workflow

1. Rebuild and restart the stack so the compose mount and new env wiring are active.
2. Follow the file with `tail -f infrastructure/demo-logs/teacher-flow.log`.
3. Start a new session in the UI.
4. Answer calibration questions.
5. Trigger roadmap generation by completing calibration.
6. Submit one weak learning answer and one strong learning answer.
7. Optionally send `/lab vector search`.
8. Open Kibana and inspect:
   - `sessions`
   - `session_interactions`
   - `knowledge_snapshots`
   - `dependency_graph`

## 9. Fast "Where Do I Look?" Reference

If you want to understand one concern quickly, start here:

- Browser state and API calls: `services/frontend/app/src/store/index.js`
- Session entrypoints in PHP: `services/backend/app/app/Http/Controllers/Api/ChatSessionController.php`
- PHP to Python bridge: `services/backend/app/app/Services/Rag/RagClient.php`
- Main workflow state machine: `services/rag-orchestrator/app/api/routes/sessions.py`
- Session transitions: `services/rag-orchestrator/app/services/session_manager.py`
- Grading behavior: `services/rag-orchestrator/app/services/grading.py`
- Roadmap generation: `services/rag-orchestrator/app/services/tuning.py`
- Learning concept rendering: `services/rag-orchestrator/app/services/learning.py`
- Session persistence: `services/rag-orchestrator/app/services/session_store.py`
- Elasticsearch writes: `services/rag-orchestrator/app/clients/elasticsearch.py`
- Embedding generation: `services/embedding-worker/app/main.py`
- External search path: `services/search-agent/app/routes/search.py`
- Model runtime configuration: `services/llm-engine/config.yaml`
- Demo flow log source wiring: `docker-compose.yml`

## 10. Final Mental Model

The simplest correct mental model for this codebase today is:

- Frontend is the conversation desk.
- Backend is the guarded API entrance.
- RAG orchestrator is the workflow brain.
- Emily the embedding worker turns text into meaning numbers.
- Louis the LLM engine judges or generates when asked.
- Elasticsearch is memory.
- Search-agent is an external scout that now feeds the roadmap-building step.
- Kibana is the observation tower that humans open manually when they want to inspect Elasticsearch.

The most important engineering truth is that this is not "one AI service." It is a coordinated multi-service workflow where most of the reliability comes from normal software engineering:

- explicit API boundaries
- persisted state
- deterministic phase transitions
- fallback behavior
- observable logs
- containerized runtime constraints

That is the bridge from "library story" to "professional system understanding."
