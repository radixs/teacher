# RAG Orchestrator Flows

This file documents the current `rag-orchestrator` runtime paths from entry point to response. It intentionally references file and function names without hard-coding line numbers, because the refactor now moves too quickly for line-accurate docs to stay useful.

Common mounting and composition points:
- `services/rag-orchestrator/app/main.py` - `app.include_router(...)` mounts the session API under `/v1`.
- `services/rag-orchestrator/app/core/service_container.py` builds the dependency graph used by FastAPI injection.

**STARTUP HYDRATION (boot the API process and preload persisted sessions):**
- `services/rag-orchestrator/app/core/application_bootstrap.py` - `lifespan()` wraps application startup and shutdown.
- `services/rag-orchestrator/app/core/application_bootstrap.py` - `startup()` resolves core dependencies and starts hydration.
- `services/rag-orchestrator/app/repositories/session_repository.py` - `list()` reads persisted session documents from Elasticsearch.
- `services/rag-orchestrator/app/clients/elasticsearch_client.py` - `search()` executes the sessions index search.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `load_session()` rehydrates each persisted session into the in-memory store.

**STARTUP FAILURE (stop the API when Elasticsearch or session storage is not ready):**
- `services/rag-orchestrator/app/core/application_bootstrap.py` - `startup()` retries only temporary connection and warm-up failures.
- `services/rag-orchestrator/app/core/application_bootstrap.py` - `startup()` raises `ApplicationBootstrapError` when Elasticsearch cannot be reached, never becomes query-ready, or the sessions index does not exist.

**HEALTHCHECK (basic liveness response):**
- `services/rag-orchestrator/app/main.py` - `healthcheck()` returns `{"status": "ok"}`.

**SHUTDOWN (close downstream HTTP clients cleanly):**
- `services/rag-orchestrator/app/core/application_bootstrap.py` - `shutdown()` closes the LLM, embedding, search, and Elasticsearch clients.

**START SESSION (create a learner session and return the first calibration question):**
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_session()` validates the request and delegates to the top-level workflow.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `start_new_session()` orchestrates calibration question generation, session creation, first assistant turn, profile persistence, interaction persistence, and final session save.
- `services/rag-orchestrator/app/services/calibration_planner_service.py` - `questions()` requires a working LLM client and delegates to `_questions_from_llm()`.
- `services/rag-orchestrator/app/clients/llm_client.py` - `generate()` sends one strict `/v1/chat/completions` request to `llm-engine`.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `create_session()` creates the in-memory session aggregate.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `next_calibration_question()` selects the first diagnostic question.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `add_message()` appends the assistant calibration question to the transcript.
- `services/rag-orchestrator/app/clients/embedding_client.py` - `embed()` creates the learner profile embedding.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `upsert_user_profile()` stores the learner profile in `user_profiles`.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `store_interaction()` stores the first assistant turn in `session_interactions`.
- `services/rag-orchestrator/app/repositories/session_repository.py` - `save()` persists the full session document in `sessions`.
- `services/rag-orchestrator/app/mappers/session_response_mapper.py` - `to_session_response_dto()` converts the internal session object into the HTTP response DTO.

**GET SESSION - IN-MEMORY HIT (resume an already loaded session):**
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `get_session()` delegates the request.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `get_session()` routes the request into `_restore_session()`.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_restore_session()` checks the in-memory session manager first.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `get_session()` returns the already loaded session.

**GET SESSION - PERSISTED RESTORE (resume a session not currently in memory):**
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_restore_session()` falls back to durable storage when memory misses.
- `services/rag-orchestrator/app/repositories/session_repository.py` - `get()` loads the persisted session document from Elasticsearch.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `load_session()` restores the persisted session into memory.
- `services/rag-orchestrator/app/mappers/session_response_mapper.py` - `to_session_response_dto()` returns the restored session in normal API form.

**GET SESSION - NOT FOUND (return HTTP 404 for an unknown session id):**
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_restore_session()` raises `SessionNotFoundError` when both memory and persistence miss.
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `get_session()` converts that miss into HTTP `404`.

**SEND MESSAGE - COMMON ENTRY (restore session, append user turn, persist interaction):**
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_message()` validates the request and delegates to the workflow layer.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `send_message()` restores the session, appends the user turn, embeds normal learner messages, stores the interaction, and dispatches by phase.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `store_interaction()` writes the learner turn into `session_interactions`.

**SEND MESSAGE - /LAB COMMAND (generate a lab primer instead of normal tutoring):**
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `send_message()` detects `/lab` before embeddings or grading.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_handle_lab_command()` resolves the requested concept, stores the command interaction, and prepares the assistant response.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_resolve_lab_concept()` chooses the explicit `/lab <topic>` argument, the current learning concept, or the session goal.
- `services/rag-orchestrator/app/services/lab_primer_service.py` - `generate()` renders the lab output package and optionally writes files when auto-write is enabled.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_render_lab_response()` formats the generated files into markdown for the UI.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_finalize_assistant_turn()` appends the assistant reply, persists it, and saves the session.

**SEND MESSAGE - CALIBRATION CONTINUES (record one answer and ask the next diagnostic question):**
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `send_message()` dispatches to `CalibrationWorkflowService` while the session phase is `calibration` or `tuning`.
- `services/rag-orchestrator/app/services/calibration_workflow_service.py` - `handle_answer()` records the answer, stores a calibration snapshot, and asks `SessionManagerService.next_calibration_question()` for the next pending question.
- `services/rag-orchestrator/app/services/calibration_planner_service.py` - `synthesize_snapshot()` builds the compact calibration snapshot document.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `store_snapshot()` writes the snapshot into `knowledge_snapshots`.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_finalize_assistant_turn()` persists the next assistant question and saves the updated session.

**SEND MESSAGE - CALIBRATION COMPLETES INTO ROADMAP AND FIRST LEARNING STEP:**
- `services/rag-orchestrator/app/services/calibration_workflow_service.py` - `handle_answer()` detects that no more calibration questions remain and transfers control to tuning.
- `services/rag-orchestrator/app/services/tuning_workflow_service.py` - `complete_calibration()` owns the calibration-to-learning handoff.
- `services/rag-orchestrator/app/services/tuning_program_generator_service.py` - `build_search_query()` derives the external resource query from the goal and calibration history.
- `services/rag-orchestrator/app/services/resource_discovery_service.py` - `discover_resources()` calls `SearchClient.search(..., enrich=False)`, normalizes results, and persists them as learning resources.
- `services/rag-orchestrator/app/clients/search_client.py` - `search()` calls `search-agent`.
- `services/rag-orchestrator/app/clients/embedding_client.py` - `embed()` computes embeddings for retained external resources.
- `services/rag-orchestrator/app/services/tuning_program_generator_service.py` - `generate()` requests a structured roadmap from the LLM and validates the returned JSON.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `set_tuning_plan()` stores the roadmap on the session.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `begin_learning()` moves the session into active learning.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `store_dependency_node()` writes each roadmap node into `dependency_graph`.
- `services/rag-orchestrator/app/services/learning_coordinator_service.py` - `build_overview()` builds the first learning concept message.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `_finalize_assistant_turn()` persists the first learning message and saves the session.

**SEND MESSAGE - LEARNING PASS TO NEXT CONCEPT:**
- `services/rag-orchestrator/app/services/learning_workflow_service.py` - `handle_answer()` selects the current concept, grades the answer, stores a learning snapshot, and decides whether to advance.
- `services/rag-orchestrator/app/services/learning_coordinator_service.py` - `current_node()` and `next_index()` determine the current and next roadmap nodes.
- `services/rag-orchestrator/app/services/exercise_grader_service.py` - `evaluate()` builds the grading prompt, calls the LLM, and parses the returned JSON.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `record_learning_outcome()` stores the concept outcome in session progress.
- `services/rag-orchestrator/app/services/session_manager_service.py` - `advance_concept()` moves the learner to the next concept.
- `services/rag-orchestrator/app/repositories/learning_memory_repository.py` - `store_snapshot()` persists the learning outcome.

**SEND MESSAGE - LEARNING RETRY (answer does not pass yet):**
- `services/rag-orchestrator/app/services/learning_workflow_service.py` - `handle_answer()` stores the failed outcome, persists the snapshot, and builds retry guidance without advancing the roadmap.

**SEND MESSAGE - LEARNING COMPLETE (final concept passes):**
- `services/rag-orchestrator/app/services/session_manager_service.py` - `advance_concept()` moves the concept index past the end of the roadmap and sets phase to `learning_complete`.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `send_message()` returns a terminal reminder for subsequent messages in the completed phase.

**STRICT FAILURE - CALIBRATION QUESTION GENERATION:**
- `services/rag-orchestrator/app/services/calibration_planner_service.py` - `_questions_from_llm()` converts timeouts, invalid JSON, invalid structures, and too-short question lists into `CalibrationQuestionGenerationError`.
- `services/rag-orchestrator/app/services/user_workflow_service.py` - `start_new_session()` refuses to create a session if no usable first calibration question exists.
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_session()` maps that failure to HTTP `503`.

**STRICT FAILURE - EXTERNAL SEARCH:**
- `services/rag-orchestrator/app/clients/search_client.py` - `search()` raises `ExternalSearchError` when the search-agent call fails or returns an unusable body.
- `services/rag-orchestrator/app/services/tuning_workflow_service.py` - `complete_calibration()` depends on real search results and does not continue silently when discovery fails.
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_message()` maps the failure to HTTP `503`.

**STRICT FAILURE - ROADMAP GENERATION:**
- `services/rag-orchestrator/app/services/tuning_program_generator_service.py` - `generate()` requires a working LLM client in strict mode.
- `services/rag-orchestrator/app/services/tuning_program_generator_service.py` - `_generate_with_llm()` raises `TuningPlanGenerationError` on timeout, invalid JSON, invalid structure, missing required fields, missing valid resources, or invalid confidence values.
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_message()` maps roadmap-generation failure to HTTP `503`.

**STRICT FAILURE - GRADING:**
- `services/rag-orchestrator/app/services/exercise_grader_service.py` - `evaluate()` raises `ExerciseGradingError` when the model times out or returns unusable output.
- `services/rag-orchestrator/app/services/exercise_grader_service.py` - `_parse_result()` rejects invalid JSON, invalid result structure, invalid score, invalid feedback, and invalid highlights.
- `services/rag-orchestrator/app/services/learning_workflow_service.py` - `handle_answer()` depends on a strict grading result and does not substitute heuristic scoring.
- `services/rag-orchestrator/app/api/routes/sessions_router.py` - `post_message()` maps grading failure to HTTP `503`.
