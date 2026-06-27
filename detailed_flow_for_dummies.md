# Detailed Flow For Dummies

This document starts with a simple library story and then gradually moves into exact technical behavior, file ownership, container boundaries, and the current implementation reality of this project.

It is written for experienced backend developers who know distributed application structure, HTTP APIs, persistence, and Docker, but do not yet have intuition for RAG, embeddings, or LLM-driven flows.

## Key Terms First

These terms appear many times in the rest of the document. Each term has two explanations:

- Library picture: the mental image.
- Technical meaning: the real implementation idea.

### Retrieval-Augmented Generation (RAG)

- Library picture: before Louis the expert librarian makes a learning plan, other librarians bring him the visitor's warm-up answers and a quick stack of outside reference cards. Louis uses those materials instead of planning from memory alone. Saved past visit cards are filed away, but the library does not yet semantically search those past cards before every answer.
- Technical meaning: an LLM response is improved by retrieving context first, then placing that context into the prompt. In this project, the active retrieval path today is roadmap generation: `search-agent` returns public resources, `rag-orchestrator` includes their readable text in the roadmap prompt, and Elasticsearch stores sessions, interactions, snapshots, vectors, resources, and roadmap nodes for persistence and future retrieval work.

### Embedding

- Library picture: Emily turns each page, question, or learner answer into a secret "shape of meaning" card. Two texts that mean similar things get cards with similar shapes.
- Technical meaning: an embedding is a numeric vector representation of text. Similar meanings produce vectors that are closer together in vector space. This project uses `bge-base-en-v1.5` with 768 dimensions.

### Vector Store and Matrices

- Library picture: instead of storing only words on cards, the library also stores long rows of numeric weights that describe meaning. In a complete semantic-retrieval flow, a new question gets its own meaning card and the catalog compares it with old cards to find the closest matches.
- Technical meaning: a vector store is a database that indexes high-dimensional numeric arrays for nearest-neighbor search. Elasticsearch stores these arrays in `dense_vector` fields. This repository already stores those vectors, but does not yet use them for vector-nearest retrieval before every LLM prompt. When people casually say "matrices" here, think "organized tables of weights used to compare meaning."

### How Embeddings Fit Into RAG

- Library picture: in a complete semantic RAG flow, if the visitor asks, "How do I make search smarter?", the librarians do not only look for cards containing the exact words "make search smarter." Emily first makes a meaning-shape card for the new question. The catalog compares that shape against the shapes already stored on old cards. Cards about "semantic retrieval," "vector search," or "relevance tuning" can be found even if they do not use the same wording. The librarians then hand Louis the actual readable notes from those cards, not the secret shape numbers.
- Technical meaning: in a RAG system, embeddings usually power the retrieval step before the LLM prompt is built. The incoming user text is embedded, Elasticsearch compares that vector to stored `dense_vector` fields, and the closest matching documents are selected. After that, the orchestrator sends the LLM normal text from those documents, such as titles, snippets, summaries, learner answers, or knowledge snapshots. The LLM does not receive the raw 768-number vectors as useful context. The vectors are for finding relevant rows; the text fields are what get appended to the model prompt.

Why not just store text?

- Exact text search only finds what shares words. If the stored note says "nearest-neighbor retrieval" and the learner asks "how does semantic memory work?", plain keyword search may miss it.
- Embeddings let the system search by meaning. That matters when learners paraphrase, use beginner vocabulary, or ask follow-up questions in a different wording from the stored resource.
- Text is still required. Embeddings help choose the best records, but the answer is grounded in the readable text attached to those records.

When is `dense_vector` used?

- In the general RAG pattern, `dense_vector` is used during the Elasticsearch retrieval query, before the final LLM prompt is assembled.
- Such an app embeds the new query, asks Elasticsearch for vector-nearest documents, receives matching rows, extracts their readable text fields, and places those text snippets into the prompt.
- The embedding itself is not the lesson content. It is the lookup key that helps find lesson content.

Current project reality:

- This project already writes embeddings into Elasticsearch for learner profiles, user interactions, knowledge snapshots, and learning resources.
- The roadmap-generation flow currently retrieves external resources through `search-agent` and DuckDuckGo, embeds those resources, stores them in `learning_resources`, and sends the readable resource text to `llm-engine`.
- The current code does not yet show an Elasticsearch vector similarity query over `dense_vector` fields before every LLM call. In other words, the vector-capable memory is being built and stored, but the full "embed new prompt -> vector-search Elasticsearch -> append matching stored text to prompt" loop is not yet active everywhere.
- Follow-up interactions do create embeddings and persist the conversation to Elasticsearch. Today, follow-up handling mainly uses the active session state, current phase, current roadmap concept, current learner answer, and stored session document. The intended RAG memory behavior is to also retrieve semantically similar earlier records for each prompt, but that retrieval step still needs explicit vector-search code before it is truly happening on every follow-up.

### BM25

- Library picture: one librarian is still very good at old-fashioned keyword lookup. If the visitor says "Elasticsearch relevance tuning," this librarian finds books where those exact words matter a lot.
- Technical meaning: BM25 is a lexical ranking algorithm. It rewards relevant term frequency and discounts overly common terms. It is excellent for exact terms and precise vocabulary.

### Semantic Search

- Library picture: even if the visitor asks "how to make search results feel smarter," a semantic catalog could still find books about "relevance tuning" because the meaning is close, not just the words.
- Technical meaning: semantic search compares embeddings instead of exact words. It is useful when the wording changes but the intent stays similar. The project stores the embeddings needed for this, but full Elasticsearch semantic retrieval is not currently wired into every prompt.

### Calibration

- Library picture: before teaching starts, the library asks a few warm-up questions to learn what the visitor already knows.
- Technical meaning: this is the first phase of the session. The current code asks the local LLM to generate personalized calibration questions from the learner goal and profile, and session creation fails explicitly if the model output is unusable.

### Tuning Roadmap

- Library picture: after calibration, the librarians draw a learning map: first shelf A, then shelf B, then shelf C, because some topics unlock later topics.
- Technical meaning: this is the ordered learning plan. The current code combines calibration answers, DuckDuckGo search results, and the local LLM to generate the roadmap, and the request fails explicitly if the returned plan is unusable.

### Context Window

- Library picture: Louis can only keep a limited stack of open notes on his desk at once.
- Technical meaning: the LLM can only process a limited amount of text per request. In `services/llm-engine/config.yaml`, the current context length is `12288`.

Model size and quality:

- Bigger models usually have more internal capacity. They often understand instructions better, connect ideas more reliably, and handle ambiguous questions with fewer mistakes.
- Smaller models are faster and cheaper to run on local hardware, but they usually have weaker reasoning, weaker instruction following, and less reliable factual recall.
- A quantized local model, such as this project's Mistral 7B `Q4_K_M`, trades some precision for memory savings and speed. That is why it can fit on practical hardware, but it may be less accurate than a larger or less-compressed model.
- No model is automatically truthful. The model predicts likely text. RAG helps by putting relevant source text into the prompt, but the model can still misunderstand, overgeneralize, or invent details if the prompt is weak, contradictory, or missing key facts.

Big context window vs small context window:

- A small context window is like a small desk. The model can only see a short prompt, a few retrieved notes, and a short conversation history. This forces the system to choose context carefully.
- A big context window is like a bigger desk. The model can see more previous turns, more documents, longer instructions, and more examples in one request.
- Bigger is useful when the answer really depends on many pages of context, but it is not magic. Long prompts are slower, use more memory, and can contain distracting or contradictory material.
- Models can also suffer from "lost in the middle": information near the start or end of a long prompt may influence the answer more strongly than important details buried in the middle.

Using only part of the context window vs filling it:

- Using a small, carefully chosen part of the window is often better than filling the whole window with everything available.
- Good RAG retrieves the most relevant text, trims duplicates, removes weak material, and sends a focused prompt.
- Filling the entire window can help if all included text is relevant and well organized.
- Filling the window with loosely related notes can make hallucination more likely, because the model may blend unrelated facts, pick the wrong source, or invent a bridge between conflicting pieces of context.
- Hallucination often happens when the model lacks enough grounding, receives noisy or contradictory context, is asked for facts not present in the prompt, or is pushed to answer even when it should say "I do not know."

How the LLM processes text and writes an answer:

- First, the input text is split into tokens. A token can be a word, part of a word, punctuation, or whitespace-like unit.
- Each token is converted into numbers called an embedding. This is the model's internal numeric form for text. It is related to the embedding idea used in RAG, but it is inside the LLM and not the same vector stored in Elasticsearch.
- The tokens then pass through many transformer layers. These layers contain learned matrices and vectors, plus attention mechanisms that let each token look at other tokens in the context.
- During inference, the text does not "fall through and then go backwards" to become an answer. The backward pass is mainly a training concept, where model weights are adjusted after errors are measured.
- During normal answering, the model does a forward pass and produces scores for possible next tokens. These scores are called logits.
- The inference server chooses the next token from those scores, using decoding settings such as temperature and sampling rules.
- The chosen token is appended to the conversation, then fed back into the model as part of the context to choose the next token.
- This repeats one token at a time until the model reaches a stop token, a token limit, or another stopping rule.
- Finally, the output token ids are decoded back into readable text and returned to the app.

### Grading Profile

- Library picture: the librarians use a scoring sheet so every exercise is judged by the same rules instead of mood.
- Technical meaning: `services/rag-orchestrator/config/grading_profiles.yaml` defines the rubric, threshold, and feedback rules used by `ExerciseGraderService`.

What it is for in the app:

- The learning phase gives the learner an exercise for the current concept.
- When the learner answers, the app asks `llm-engine` to grade that answer.
- The grading profile tells the LLM what "good enough" means. Today the default profile scores coverage, practical application, and clarity.
- The profile also defines the pass threshold. In the current config, the answer must reach `0.6` or higher to pass.
- The grading profile is not the learner's lesson plan. It is the judge's rule sheet used after the learner submits an answer.

Plain example:

- Learner concept: "Embeddings and vector search"
- Exercise: "Describe how embeddings enable semantic retrieval."
- Learner answer: "Embeddings turn text into vectors so similar meanings can be compared."
- Grading profile asks:
  - Did they cover the key concept?
  - Did they connect it to a practical scenario?
  - Was the answer clear enough?
- The LLM must return JSON with `passed`, `score`, `feedback`, and `highlights`.

### HIP Acceleration

- Library picture: Louis can answer using only desk work, or he can ask a very fast helper machine in the back room to speed up heavy thinking.
- Technical meaning: HIP is the AMD ROCm path used by llama.cpp to offload inference work to the Radeon GPU. This project is now configured to offload all 32 Mistral layers by default on the target RX 6600, while CPU fallback remains available through a simple `.env` switch: `LLM_ACCELERATION_MODE=cpu`.

### Dependency Graph

- Library picture: a string map on the wall shows which books must be read before other books make sense.
- Technical meaning: the roadmap is stored as concept nodes with prerequisites. Elasticsearch index `dependency_graph` is used to persist these nodes.

What it is for in the app:

- After calibration, the system generates a learning roadmap.
- Each roadmap item becomes one concept node: concept id, concept name, summary, difficulty, exercise, resources, and prerequisites.
- Prerequisites tell the app which ideas should come before other ideas.
- The current runtime mostly walks the session's roadmap in order with `current_concept_index`; storing the same concept nodes as a graph-like structure makes the plan inspectable in Elasticsearch and easier to extend later.
- The dependency graph is not the vector store and not the grading rubric. It is the saved structure of "what should be learned, in what relationship to other concepts."

Plain example:

- Node 1: "Basic embeddings"
  - prerequisites: none
- Node 2: "Vector search"
  - prerequisites: "Basic embeddings"
- Node 3: "Hybrid retrieval"
  - prerequisites: "Vector search"

That means the learner should understand embeddings before vector search, and vector search before hybrid retrieval.

## Professional-Only Summary As A Multi-Session User Story

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
10. `services/rag-orchestrator/app/api/routes/sessions_router.py::post_session()` acts as a thin controller and delegates to `UserWorkflowService.start_new_session()`.
11. `CalibrationPlannerService.questions()` asks `llm-engine` for a personalized question list and fails explicitly if the model output is unusable.
12. `SessionManagerService.create_session()` creates the aggregate and `SessionManagerService.next_calibration_question()` selects the first question.
13. Learner profile text is embedded and stored in Elasticsearch `user_profiles` through `LearningMemoryRepository`.
14. First assistant message is persisted to `session_interactions`.
15. Full session snapshot is persisted to `sessions`.
16. `session_response_mapper.py` shapes the public response DTO.
17. Response returns to frontend, which stores `sessionId`, `phase`, transcript, and local session history.

### Session 1: Calibration Progress

1. User submits answer through `ChatInput`.
2. Vuex `sendMessage` optimistically appends the user message locally.
3. Backend `ChatSessionController::message()` validates request and forwards it.
4. FastAPI `post_message()` is a thin controller and delegates to `UserWorkflowService.send_message()`.
5. `EmbeddingClient.embed()` calls `embedding-worker /embed`.
6. User interaction with embedding is stored in `session_interactions` through `LearningMemoryRepository`.
7. `CalibrationWorkflowService.handle_answer()` writes the calibration answer into `calibration_history`.
8. `CalibrationWorkflowService` synthesizes and persists the calibration snapshot in `knowledge_snapshots`.
9. `CalibrationWorkflowService` generates the next question from the queue and returns it.
10. Session is saved again in `sessions`.

### Session 2: User Returns Later

1. Browser still has `teacher.activeSessionId` and `teacher.sessionHistory`.
2. On page load, Vuex `hydrateFromStorage()` dispatches `loadSession`.
3. Backend `show()` endpoint proxies to `rag-orchestrator`.
4. FastAPI `get_session()` delegates to `UserWorkflowService.get_session()`.
5. If the session is not currently in memory, `SessionRepository.get()` reads it from Elasticsearch.
6. The user sees the existing transcript and current phase.

### Session 2: Calibration Finishes And Learning Starts

1. Final calibration answer is posted.
2. `CalibrationWorkflowService.handle_answer()` detects no more calibration questions and hands off to `TuningWorkflowService.complete_calibration()`.
3. `TuningWorkflowService` creates an external search query from the goal and calibration answers.
4. `ResourceDiscoveryService.discover_resources()` calls `search-agent` through `SearchClient.search(..., enrich=False)` and normalizes the returned public resources.
5. Retrieved resources are embedded and stored in `learning_resources`.
6. `TuningProgramGeneratorService.generate()` asks `llm-engine` for a structured roadmap using calibration answers plus retrieved resources.
7. `SessionManagerService.set_tuning_plan()` stores roadmap.
8. `SessionManagerService.begin_learning()` moves phase to `learning`.
9. Each roadmap node is written to `dependency_graph`, and concept resources are also stored in `learning_resources`.
10. `LearningCoordinatorService.build_overview()` creates the first concept message.
11. Assistant returns concept summary, resources, and exercise.

### Session 3: First Learning Exercise

1. User studies resources and submits exercise answer.
2. `UserWorkflowService.send_message()` enters the `session.phase == "learning"` branch.
3. `LearningWorkflowService.handle_answer()` selects the current concept through `LearningCoordinatorService.current_node()`.
4. `ExerciseGraderService.evaluate()` builds prompt using concept and rubric.
5. `LlmClient.generate()` calls `llm-engine` through strict chat-completions behavior.
6. Result is parsed only if valid JSON; otherwise the request fails explicitly.
7. `LearningWorkflowService` stores the snapshot of learning outcome in `knowledge_snapshots`.
8. If passed, concept advances; otherwise retry feedback is returned.
9. Assistant response is stored in `session_interactions` through `LearningMemoryRepository`.
10. Session is persisted to `sessions`.

### Session 3: Optional Lab Request

1. User sends `/lab vector search`.
2. `UserWorkflowService.send_message()` branches before normal learning evaluation.
3. `LabPrimerService.generate()` renders lab files from templates.
4. Assistant returns fenced file content.
5. Session is persisted normally.

### Session 4 And Beyond: Continued Learning Until Completion

1. User repeatedly resumes session from local storage and server state.
2. Each successful answer advances `current_concept_index`.
3. Each failed answer keeps the same index and returns feedback.
4. Once last concept passes, phase becomes `learning_complete`.
5. Session remains loadable through the same resume flow.
