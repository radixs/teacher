# Manual Tests

This file is a practical runbook for manually testing the current project end to end.

It focuses on:

- what to click or type in the Vue frontend
- what you should see in the UI
- what should appear in the browser `Live Flow Console`
- what should appear in `infrastructure/demo-logs/teacher-flow.log`
- what each test proves about the system

Use this file while the app is open in one browser tab. The preferred observer is the `Live Flow Console` at the bottom of the chat screen. The terminal log file is now optional if you want the raw host-level trace too.

## 1. Goal

After finishing this runbook, you should have manually verified:

- frontend -> backend -> rag-orchestrator wiring
- LLM-driven calibration question generation
- profile embedding + `user_profiles` persistence
- calibration answer persistence + `knowledge_snapshots`
- search-agent participation in roadmap generation
- learning resource ingestion into `learning_resources`
- roadmap persistence into `dependency_graph`
- grading path through `llm-engine`
- heuristic grading fallback visibility if the model output is bad
- session persistence and resume from Elasticsearch
- `/lab` generation
- Kibana inspection of the stored documents

## 2. One-Time Warning Before Testing

The Elasticsearch templates changed recently.

If your current Elasticsearch data volume comes from an older run, the stored mappings may not match the current code anymore.

If you want the cleanest possible manual test, do a fresh reset first.

This deletes persisted Docker volumes for this project:

```bash
make clean
make up
make bootstrap-es
```

If you do not want a full reset, at minimum make sure the affected indices were recreated after the mapping changes.

If `make bootstrap-es` stops with a message like `exists but has no mapped properties`, those indices were created during an older broken bootstrap run and must be deleted before retesting.

Delete only the affected app indices, then rerun bootstrap:

```bash
curl -X DELETE http://localhost:9200/knowledge_snapshots
curl -X DELETE http://localhost:9200/learning_resources
curl -X DELETE http://localhost:9200/session_interactions
make bootstrap-es
```

## 3. Recommended Test Setup

Open 4 terminals plus 2 browser tabs.

### Terminal 1: stack control

```bash
cd /home/radix/www/teacher
make up
```

### Terminal 2: optional shared flow log

Clear the old log if you want a clean narrative:

```bash
make truncate-log
tail -f infrastructure/demo-logs/teacher-flow.log
```

### Terminal 3: container status

```bash
make ps
```

### Terminal 4: optional container logs

```bash
make logs
```

### Browser tab 1: frontend

- `http://localhost:3000`

### Browser tab 2: Kibana

- `http://localhost:5601`

You do not need Kibana for every test, but keep it ready for the data-inspection steps.

## 4. What Counts As A Healthy Startup

Before using the frontend, the system should eventually show healthy signals like:

- In the browser `Live Flow Console`, fresh runtime events should start appearing once you begin interacting with the app.
- In the optional shared file log, you should eventually see:

- `rag-orchestrator | startup.started`
- `rag-orchestrator | startup.completed`
- `llm-engine | config.loaded`
- `llm-engine | server.starting`
- `search-agent | startup.completed`

Possible first-run entries:

- `llm-engine | model.download.started`
- `llm-engine | model.download.completed`
- `rag-orchestrator | startup.waiting_for_elasticsearch`
- `rag-orchestrator | startup.bootstrap_pending`

Notes:

- `embedding-worker` does not fully announce itself at startup in the shared log. Its first visible proof is usually `embedding-worker | model.loaded` on the first embedding request.
- `startup.waiting_for_elasticsearch` is normal during fresh boots while Elasticsearch is still coming up.
- `startup.completed` for `rag-orchestrator` may appear a bit later than the other startup lines. On a fresh restart it can legitimately take 10-20 seconds while Elasticsearch moves from connection failures to temporary `503` warm-up responses and then becomes query-ready.
- `startup.bootstrap_pending` is normal after `make up` on a fresh reset and means the app is waiting for `make bootstrap-es` to create the indices.
- If the shared log stays completely empty after `make up`, you are not looking at a healthy stack. At that point check `docker compose logs rag-orchestrator search-agent llm-engine`.
- If the `Live Flow Console` shows `Reconnecting`, refresh the page once after the backend is healthy. The frontend keeps only a short rolling window of recent pushed events and does not persist them locally.
- `make restart` now clears the backend event buffer for the `Live Flow Console`, so a fresh restart gives you a clean demo timeline in the browser.
- GPU offload verification for `llm-engine` is not written into the shared flow file. Check `docker compose logs --tail=200 llm-engine` and expect `ggml_cuda_init: found 1 ROCm devices` plus `load_tensors: offloaded 32/33 layers to GPU`.
- To switch the chat model back to CPU later, set `LLM_ACCELERATION_MODE=cpu` in `.env` and run `make restart`. The current default is `LLM_ACCELERATION_MODE=gpu`.

## 5. Test Case 1: Open The Frontend With No Active Session

### Action

1. Open `http://localhost:3000`.
2. Do not start a session yet.

### Expected UI

- You should see the "Start New Session" form.
- There should be no active goal in the sidebar.

### Expected shared log

If localStorage does not contain a previous active session:

- usually no new lines appear

If localStorage still contains a previous session id:

- `backend | http.sessions.show.received`
- `backend | rag.fetch_session.dispatch`
- `rag-orchestrator | api.sessions.show.received`
- either:
  - `rag-orchestrator | api.sessions.show.completed`
  - or:
    - `elasticsearch | document.hit`
    - `rag-orchestrator | session_store.hit`
    - `rag-orchestrator | session.registered`
    - `rag-orchestrator | api.sessions.show.restored`
    - `rag-orchestrator | api.sessions.show.completed`

### What this proves

- frontend boot works
- local resume path works if there is a stored session id
- absence of frontend log lines is expected because browser code does not write to the shared file directly

## 6. Test Case 2: Start A New Session

### Action

In the frontend:

1. Enter a goal such as:
   - `Become comfortable designing Elasticsearch-backed RAG systems`
2. Enter a background summary such as:
   - `Senior PHP developer, good with APIs and Docker, little hands-on experience with embeddings and vector search.`
3. Click `Start Session`.

### Expected UI

- Sidebar should show the active goal.
- Phase should become `Calibration`.
- The first assistant question should appear.
- A session entry should appear in the sidebar history.

### Expected shared log: happy path

You should see a sequence close to this:

- `backend | http.sessions.start.received`
- `backend | http.sessions.start.validated`
- `backend | rag.start_session.dispatch`
- `rag-orchestrator | api.sessions.start.received`
- `llm-engine | completion.requested`
- either:
  - `llm-engine | completion.received`
  - or:
    - `llm-engine | completion.chat_failed`
    - `llm-engine | completion.received`
- either:
  - `rag-orchestrator | calibration.questions.generated`
  - or:
    - `rag-orchestrator | calibration.questions.fallback`
- `rag-orchestrator | session.created`
- `rag-orchestrator | calibration.question.selected`
- `rag-orchestrator | message.appended`
- `embedding-worker | embed.received`
- `embedding-worker | model.loaded` on first embed only
- `embedding-worker | embed.completed`
- `elasticsearch | user_profile.upserted`
- `elasticsearch | interaction.stored`
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.start.completed`
- `backend | rag.start_session.response`
- `backend | http.sessions.start.completed`

### What this proves

- frontend form submission works
- backend validation works
- rag-orchestrator session creation works
- calibration question generation is LLM-driven first
- learner profile embedding is generated
- `user_profiles`, `session_interactions`, and `sessions` are written

## 7. Test Case 3: Answer A Normal Calibration Question

### Action

Reply to the first calibration question with a realistic answer, for example:

`I have strong general backend experience and have used Elasticsearch only at a basic level for keyword search. I do not yet understand embeddings or hybrid retrieval in practice.`

### Expected UI

- Your message appears.
- The assistant asks the next calibration question.
- Phase remains `Calibration`.

### Expected shared log

You should see:

- `backend | http.sessions.message.received`
- `backend | http.sessions.message.validated`
- `backend | rag.send_message.dispatch`
- `rag-orchestrator | api.sessions.message.received`
- `rag-orchestrator | message.appended`
- `embedding-worker | embed.received`
- `embedding-worker | embed.completed`
- `elasticsearch | interaction.stored`
- `rag-orchestrator | calibration.processing`
- `rag-orchestrator | calibration.answer.recorded`
- `elasticsearch | snapshot.stored`
- `rag-orchestrator | calibration.snapshot.created`
- `rag-orchestrator | calibration.question.selected`
- `rag-orchestrator | message.appended`
- `rag-orchestrator | calibration.next_question`
- `elasticsearch | interaction.stored`
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.message.completed`
- `backend | rag.send_message.response`
- `backend | http.sessions.message.completed`

### What this proves

- calibration answers are embedded
- user turns are stored in `session_interactions`
- calibration summaries are stored in `knowledge_snapshots`
- session save after each turn works

## 8. Test Case 4: Finish Calibration And Trigger Roadmap Generation

### Action

Keep answering calibration questions until the assistant stops asking questions and instead returns the learning roadmap intro.

Use detailed answers, not one-word replies.

### Expected UI

After the last calibration answer:

- phase changes from `Calibration` to `Learning`
- the assistant returns a roadmap summary
- the first learning concept appears
- the message contains resources and an exercise

### Expected shared log: key events

For the final calibration answer, you should see the normal message/embedding sequence first, then:

- `rag-orchestrator | calibration.processing`
- `rag-orchestrator | calibration.answer.recorded`
- `rag-orchestrator | calibration.snapshot.created`
- `rag-orchestrator | calibration.question.exhausted`

Then the search-backed roadmap flow:

- `search-agent | search.requested` from the orchestrator client boundary
- `search-agent | search.received` from the search service
- `search-agent | duckduckgo.requested`
- `search-agent | duckduckgo.completed`
- `search-agent | search.completed`
- `rag-orchestrator | search.resources.selected`

Do not expect `scraper.requested` during the normal frontend roadmap flow anymore.

The main learner request now uses `enrich=false` on purpose so roadmap generation stays responsive. Page scraping is still implemented in `search-agent`, but it is no longer part of the synchronous frontend-driven session path.

Then resource ingestion:

- multiple `embedding-worker | embed.received`
- multiple `embedding-worker | embed.completed`
- multiple `elasticsearch | learning_resource.stored`

Then roadmap generation:

- `llm-engine | completion.requested`
- usually `llm-engine | completion.received`
- either:
  - `rag-orchestrator | tuning.plan.generated`
  - or:
    - `rag-orchestrator | tuning.plan.fallback`

Then session transition:

- `rag-orchestrator | tuning.plan.created`
- `rag-orchestrator | learning.started`
- multiple `elasticsearch | dependency_node.stored`
- possibly more `elasticsearch | learning_resource.stored` for concept resources
- `rag-orchestrator | learning.plan_ready`
- `elasticsearch | interaction.stored`
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.message.completed`

### What this proves

- search-agent is now part of the main flow
- external resources are stored in `learning_resources`
- roadmap generation is LLM-driven first
- fallback roadmap generation is still available
- `dependency_graph` is now filled from the real tuning flow

## 9. Test Case 5: Inspect Data In Kibana After Roadmap Generation

### Action

Open Kibana and inspect these indices:

- `sessions`
- `session_interactions`
- `knowledge_snapshots`
- `user_profiles`
- `learning_resources`
- `dependency_graph`

If you use Discover, filter by the current session id.

### Expected data

In `sessions`:

- one session document
- `phase` should be `learning`
- `tuning_plan` should be populated

In `session_interactions`:

- one assistant document for session start
- alternating user/assistant turn documents for calibration
- one assistant document for the learning intro

In `knowledge_snapshots`:

- one snapshot per answered calibration question

In `user_profiles`:

- one document keyed by the session id
- `goal`
- `experience_summary`
- `knowledge_vector`

In `learning_resources`:

- external search results
- concept resources saved from the roadmap
- vector embeddings present on stored resources

In `dependency_graph`:

- one document per concept in the roadmap

### Important clarification about Kibana

Kibana is not part of the automatic learner flow.

That means:

- the frontend never calls Kibana
- backend never calls Kibana
- rag-orchestrator never calls Kibana

Kibana is just a browser dashboard for humans to inspect Elasticsearch manually.

## 10. Test Case 6: Submit A Weak Learning Answer And Check Retry Path

### Action

On the first learning concept, intentionally submit a weak answer such as:

`I am not sure. Elasticsearch stores data and search works somehow.`

### Expected UI

Most likely:

- assistant returns corrective feedback
- phase remains `Learning`
- assistant stage is retry-style behavior, not next-concept behavior

Possible outcomes:

- ideal retry path:
  - assistant metadata stage is `learning_retry`
- if the LLM is too generous, you may unexpectedly pass
  - in that case continue with the next concept and retry this weak-answer test there, or start a new session

### Expected shared log

You should see:

- `rag-orchestrator | learning.evaluation.started`
- `rag-orchestrator | grading.started`
- `llm-engine | completion.requested`
- one of:
  - `rag-orchestrator | grading.llm_result`
  - `rag-orchestrator | grading.heuristic_fallback`
- `rag-orchestrator | learning.outcome.recorded`
- `elasticsearch | snapshot.stored`
- `rag-orchestrator | learning.evaluation.completed`
- `rag-orchestrator | message.appended`
- `elasticsearch | interaction.stored`
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.message.completed`

If the retry path is taken, the final backend completion log should contain stage `learning_retry`.

### What this proves

- grading is called from the learning path
- failures do not crash the session
- feedback is persisted
- heuristic fallback is visible if model output is malformed

## 11. Test Case 7: Submit A Strong Learning Answer And Check Pass Path

### Action

Submit a strong, structured answer for the current concept. Use:

- concrete Elasticsearch terms
- process explanation
- an experiment or evaluation idea

Example:

`An Elasticsearch index groups documents and settings, shards split the index for storage and parallelism, and each document is the searchable JSON unit. During ingestion, mappings and analyzers shape how fields are stored. During search, analyzers, BM25 scoring, and query structure affect ranking. To validate quality, I would compare baseline keyword retrieval with a hybrid approach and evaluate recall, relevance, and latency.`

### Expected UI

Usually one of:

- assistant stage `learning_next`
- assistant stage `learning_complete` if this was the last concept

### Expected shared log

You should see:

- `rag-orchestrator | learning.evaluation.started`
- `rag-orchestrator | grading.started`
- usually `rag-orchestrator | grading.llm_result`
- `rag-orchestrator | learning.outcome.recorded`
- `elasticsearch | snapshot.stored`
- `rag-orchestrator | learning.evaluation.completed`
- `rag-orchestrator | learning.concept.advanced`
- `rag-orchestrator | message.appended`
- `elasticsearch | interaction.stored`
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.message.completed`

### What this proves

- pass path works
- concept advancement works
- next concept rendering works
- completion path can eventually be reached

## 12. Test Case 8: Generate A Lab Primer Through The Frontend

### Action

Send one of these messages through the normal chat input:

- `/lab`
- `/lab vector search`
- `/lab rag evaluation`

### Expected UI

- assistant returns a generated mini project recipe
- response contains:
  - `README.md`
  - `docker-compose.yml`
  - `Makefile`
  - `notes.md`

### Expected shared log

You should see:

- `backend | http.sessions.message.received`
- `backend | rag.send_message.dispatch`
- `rag-orchestrator | api.sessions.message.received`
- `rag-orchestrator | message.appended`
- `rag-orchestrator | lab_primer.generated`
- `elasticsearch | interaction.stored` for the user command
- `rag-orchestrator | message.appended` for the assistant response
- `elasticsearch | interaction.stored` for the assistant response
- `elasticsearch | document.upserted`
- `rag-orchestrator | session_store.saved`
- `rag-orchestrator | api.sessions.message.completed`

### What this proves

- command branch handling works
- lab generation is independent from grading/search
- session persistence still works on command-style messages

## 13. Test Case 9: Resume The Session

### Action

Use one of these:

1. Refresh the browser tab.
2. Click the current session in the sidebar.
3. Close and reopen the app while keeping browser localStorage intact.

### Expected UI

- existing chat transcript is restored
- active goal is restored
- current phase is restored

### Expected shared log

You should see:

- `backend | http.sessions.show.received`
- `backend | rag.fetch_session.dispatch`
- `rag-orchestrator | api.sessions.show.received`

If the session is still in the in-memory store:

- `rag-orchestrator | api.sessions.show.completed`

If the session had to be restored from Elasticsearch:

- `elasticsearch | document.hit`
- `rag-orchestrator | session_store.hit`
- `rag-orchestrator | session.registered`
- `rag-orchestrator | api.sessions.show.restored`
- `rag-orchestrator | api.sessions.show.completed`

Then:

- `backend | rag.fetch_session.response`
- `backend | http.sessions.show.completed`

### What this proves

- resume flow works
- `sessions` documents are usable after persistence
- local browser history + server state align

## 14. Test Case 10: Optional End-Of-Program Behavior

### Action

Keep completing concepts until the roadmap is exhausted, then send one more normal chat message.

### Expected UI

- after final concept pass, assistant stage becomes `learning_complete`
- after that, another message should produce:
  - `Learning program already completed. Use /no more to wrap up or ask for a recap.`

### Expected shared log

On the final successful concept:

- `rag-orchestrator | learning.concept.advanced`
- `backend | http.sessions.message.completed` with stage `learning_complete`

On a later post-completion message:

- normal message receipt logs
- `rag-orchestrator | message.appended`
- `elasticsearch | interaction.stored`
- final stage `complete` in `api.sessions.message.completed`

### What this proves

- completion guard branch works

## 15. What To Treat As Warning Signals

These log lines do not always mean total failure, but they mean you should inspect behavior closely.

### Calibration warnings

- `rag-orchestrator | calibration.questions.fallback`

Meaning:

- LLM question generation failed
- fallback question list was used

### Roadmap warnings

- `rag-orchestrator | tuning.plan.fallback`

Meaning:

- LLM roadmap generation failed
- fallback adaptive curriculum was used

### Search warnings

- `search-agent | search.fallback`
- `search-agent | search.failed`

Meaning:

- full search flow degraded
- roadmap generation continued without external results

Only expect `search-agent | search.enrich_skipped` if you manually exercise `search-agent` with `enrich=true`. It is not part of the normal frontend session flow anymore.

### LLM warnings

- `llm-engine | completion.chat_failed`
- `llm-engine | completion.failed`

Meaning:

- chat-completions endpoint failed
- legacy completion fallback may have been used
- or the LLM was unavailable entirely

### Grading warnings

- `rag-orchestrator | grading.heuristic_fallback`

Meaning:

- the grader did not receive usable JSON from the model
- local scoring logic was used instead

### Resume warnings

- `elasticsearch | document.miss`
- `rag-orchestrator | session_store.miss`

Meaning:

- frontend asked for a session id that no longer exists in Elasticsearch

## 16. Minimum Successful Manual Test Definition

If you want a quick "go / no-go" definition, the project is manually healthy if all of these happen:

1. You can start a session from the frontend.
2. At least one calibration answer round-trip works.
3. Final calibration triggers search-agent and produces a learning roadmap.
4. `user_profiles`, `sessions`, `session_interactions`, `knowledge_snapshots`, `learning_resources`, and `dependency_graph` all contain data in Kibana.
5. One weak learning answer causes retry or at least shows a grading event.
6. One strong learning answer advances to the next concept.
7. `/lab` returns the generated files.
8. Refreshing the browser restores the session.

## 17. Suggested Demo Order

If this is for a presentation, use this sequence:

1. Clean/reset the stack if needed.
2. Start log tail.
3. Open frontend and Kibana side by side.
4. Start new session.
5. Answer 2 calibration questions slowly so the audience can see the log.
6. Fast-forward through the remaining calibration questions.
7. Pause on the roadmap-generation step and point at:
   - search-agent logs
   - learning resource writes
   - dependency graph writes
8. Submit one weak answer.
9. Submit one strong answer.
10. Run `/lab vector search`.
11. Refresh the page to prove resume.
12. Show stored docs in Kibana.

That sequence demonstrates almost every moving part without needing to complete the full curriculum.
