# Rollout Plan

| Step | Description | Status | Notes |
| --- | --- | --- | --- |
| 1 | Establish documentation + governance scaffolding (`AGENTS.md`, README stub, `.env` templates) | completed | Added `AGENTS.md`, README scaffold, and `.env.dist`. |
| 2 | Define container orchestration skeleton (docker-compose, Makefile targets, base Dockerfiles) | completed | Added compose file, Makefile, placeholders for service Dockerfiles. |
| 3 | Scaffold backend Laravel 12 project with service boundaries + config stubs | completed | Added Laravel skeleton, service wiring, env/config stubs, Dockerfile + entrypoint. |
| 4 | Scaffold Vue 3 + Vuex SPA with chat shell + API adapters | completed | Added Vite Vue app, store, chat UI, Docker entrypoint + compose wiring. |
| 5 | Build Python RAG orchestrator service (FastAPI) with embedding + LLM client interfaces | completed | Added FastAPI app, in-memory session manager, HTTP clients & Docker image. |
| 6 | Package llama.cpp service with model download/init scripts for Mistral 7B Q4_K_M | completed | Added llama.cpp build image, config-driven entrypoint, compose volume wiring. |
| 7 | Package embedding worker using `bge-base-en-v1.5` and expose embedding endpoint | completed | Added FastAPI embed service, model caching, Docker image + compose volume. |
| 8 | Configure Elasticsearch 9.1.4 container, index templates, and bootstrap scripts | completed | Added index templates, bootstrap script, compose volume + Make target. |
| 9 | Implement DuckDuckGo search agent + web scraper for resource ingestion | completed | Added FastAPI search service, scraper, Docker image, compose wiring. |
| 10 | Implement calibration phase flows (profile capture, diagnostic Q&A, persistence) | completed | Added calibration planner, stateful session flow, ES persistence for answers. |
| 11 | Implement tuning program generator (dependency graph authoring + storage) | completed | Added tuning generator, ES persistence, session phase transition. |
| 12 | Implement learning phase (lesson delivery, resource linking, exercise prompts) | completed | Added learning coordinator, lesson messaging, progress tracking + tests. |
| 13 | Implement exercise grading pipeline + configurable rubrics | pending |  |
| 14 | Build lab primer generator + temp recipe handling | pending |  |
| 15 | Implement automated test suites (`make test`: containers, API with stubs, RAG integration, UI e2e) | pending |  |
| 16 | Finalize documentation (README usage guide, update rollout + agents, polish) | pending |  |
