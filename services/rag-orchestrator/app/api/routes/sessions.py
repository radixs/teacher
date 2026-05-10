from __future__ import annotations

import html
import re
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from ...core.config import Settings, get_settings
from ...core.flow_logger import log_flow
from ...core.dependencies import (
    get_elasticsearch_client,
    get_embedding_client,
    get_llm_client,
    get_search_client,
    get_session_manager,
    get_exercise_grader,
    get_lab_primer,
    get_session_store,
)
from ...clients.elasticsearch import ElasticsearchClient
from ...clients.embedding import EmbeddingClient
from ...clients.llm import LlmClient
from ...clients.search import SearchClient
from ...services.grading import ExerciseGrader
from ...services.lab_primer import LabPrimer
from ...services.session_store import SessionStore
from ...models.api import (
    MessageModel,
    SessionMessageRequest,
    SessionMessageResponse,
    SessionModel,
    SessionStartRequest,
)
from ...models.session import Message
from ...services.calibration import CalibrationPlanner
from ...services.learning import LearningCoordinator
from ...services.tuning import TuningProgramGenerator
from ...services.session_manager import SessionManager

router = APIRouter(prefix="/sessions", tags=["sessions"])

SessionStartPayload = Annotated[SessionStartRequest, Body(..., embed=False)]
SessionMessagePayload = Annotated[SessionMessageRequest, Body(..., embed=False)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ElasticClientDep = Annotated[ElasticsearchClient, Depends(get_elasticsearch_client)]
EmbeddingClientDep = Annotated[EmbeddingClient, Depends(get_embedding_client)]
SearchClientDep = Annotated[SearchClient, Depends(get_search_client)]
LlmClientDep = Annotated[LlmClient, Depends(get_llm_client)]
ExerciseGraderDep = Annotated[ExerciseGrader, Depends(get_exercise_grader)]
LabPrimerDep = Annotated[LabPrimer, Depends(get_lab_primer)]
SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]


def _serialize_message(message: Message) -> MessageModel:
    return MessageModel(
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata,
    )


def _serialize_session(session) -> SessionModel:
    return SessionModel(
        id=session.id,
        goal=session.goal,
        phase=session.phase,
        profile=session.profile or {},
        messages=[_serialize_message(msg) for msg in session.messages],
        created_at=session.created_at,
        updated_at=session.updated_at,
        tuning_plan=session.tuning_plan or [],
    )


def _preview(value: str | None) -> str | None:
    if value is None:
        return None
    return value if len(value) <= 140 else value[:137] + "..."


def _profile_summary(profile: dict[str, Any] | None) -> str:
    return str((profile or {}).get("summary") or "").strip()


def _profile_text(goal: str, profile: dict[str, Any] | None) -> str:
    summary = _profile_summary(profile)
    if not summary:
        return goal
    return f"Goal: {goal}\nBackground: {summary}"


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    normalized = re.sub(r"\s+", " ", html.unescape(without_tags))
    return normalized.strip()


def _normalize_search_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for result in payload.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        title = str(result.get("title") or "").strip()
        url = str(result.get("url") or "").strip()
        if not title or not url:
            continue
        summary = _clean_text(result.get("snippet") or result.get("content") or "")
        content = _clean_text(result.get("content") or "")
        resources.append(
            {
                "title": title,
                "url": url,
                "summary": summary,
                "content": content,
                "snippet": _clean_text(result.get("snippet") or ""),
                "type": str(result.get("type") or "search_result"),
                "source": "duckduckgo",
            }
        )
    return resources


async def _persist_learning_resources(
    *,
    elastic_client: ElasticsearchClient,
    embedding_client: EmbeddingClient,
    index: str,
    session_id: str,
    resources: list[dict[str, Any]],
    concept_id: str | None = None,
    extra_tags: list[str] | None = None,
) -> None:
    seen_urls: set[str] = set()
    for resource in resources:
        title = str(resource.get("title") or "").strip()
        url = str(resource.get("url") or "").strip()
        if not title or not url or url in seen_urls:
            continue
        seen_urls.add(url)
        summary = _clean_text(resource.get("summary") or "")
        content = _clean_text(resource.get("content") or "")
        snippet = _clean_text(resource.get("snippet") or summary)
        resource_text = "\n".join(part for part in [title, summary, content] if part)
        embedding = await embedding_client.embed(resource_text) if resource_text else []
        tags = [
            tag
            for tag in (extra_tags or [])
            if isinstance(tag, str) and tag.strip()
        ]
        await elastic_client.store_learning_resource(
            index=index,
            resource={
                "title": title,
                "url": url,
                "source": resource.get("source", "generated"),
                "type": resource.get("type", "reference"),
                "summary": summary,
                "content": content,
                "snippet": snippet,
                "tags": list(dict.fromkeys(tags)),
                "session_id": session_id,
                "concept_id": concept_id,
            },
            embedding=embedding or None,
        )


@router.post("", response_model=SessionModel)
async def start_session(
    payload: SessionStartPayload,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
    elastic_client: ElasticClientDep,
    embedding_client: EmbeddingClientDep,
    search_client: SearchClientDep,
    llm_client: LlmClientDep,  # kept for future orchestration hooks
    session_store: SessionStoreDep,
) -> SessionModel:
    _ = search_client

    log_flow(
        "rag-orchestrator",
        "api.sessions.start.received",
        "RAG orchestrator received a request to start a new learning session.",
        goal=payload.goal,
        has_profile=bool(payload.profile),
    )

    planner = CalibrationPlanner(goal=payload.goal, profile=payload.profile)
    calibration_questions = await planner.questions(llm_client)

    session = session_manager.create_session(
        goal=payload.goal,
        profile=payload.profile,
        calibration_questions=calibration_questions,
    )

    question = session_manager.next_calibration_question(session.id)
    if question is None:
        question = "Let's begin with a quick summary of what you already know."

    assistant_message = Message(
        role="assistant",
        content=question,
        metadata={"phase": session.phase, "stage": "calibration"},
    )
    session_manager.add_message(session.id, assistant_message)

    indices = settings.indices
    profile_embedding = await embedding_client.embed(_profile_text(payload.goal, payload.profile))
    await elastic_client.upsert_user_profile(
        index=indices["user_profiles"],
        document_id=session.id,
        goal=payload.goal,
        experience_summary=_profile_summary(payload.profile),
        knowledge_vector=profile_embedding or None,
    )

    await elastic_client.store_interaction(
        index=indices["session_interactions"],
        session_id=session.id,
        role="assistant",
        content=assistant_message.content,
        turn=session.current_turn(),
        metadata=assistant_message.metadata,
        phase=session.phase,
    )

    persisted_session = session_manager.get_session(session.id)
    await session_store.save(persisted_session)
    log_flow(
        "rag-orchestrator",
        "api.sessions.start.completed",
        "RAG orchestrator initialized the session, stored the first assistant turn, and persisted the session.",
        session_id=persisted_session.id,
        phase=persisted_session.phase,
    )
    return _serialize_session(persisted_session)


@router.post("/{session_id}", response_model=SessionMessageResponse)
async def send_message(
    session_id: str,
    payload: SessionMessagePayload,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
    embedding_client: EmbeddingClientDep,
    elastic_client: ElasticClientDep,
    search_client: SearchClientDep,
    llm_client: LlmClientDep,
    exercise_grader: ExerciseGraderDep,
    lab_primer: LabPrimerDep,
    session_store: SessionStoreDep,
) -> SessionMessageResponse:
    log_flow(
        "rag-orchestrator",
        "api.sessions.message.received",
        "RAG orchestrator received a learner message for an existing session.",
        session_id=session_id,
        message_preview=_preview(payload.message),
        has_metadata=bool(payload.metadata),
    )
    try:
        session = session_manager.get_session(session_id)
    except KeyError as exc:
        stored = await session_store.get(session_id)
        if not stored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        session_manager.register_session(stored)
        session = session_manager.get_session(session_id)
        log_flow(
            "rag-orchestrator",
            "api.sessions.message.restored",
            "RAG orchestrator restored the session from Elasticsearch before processing the message.",
            session_id=session_id,
            phase=session.phase,
        )

    user_message = Message(role="user", content=payload.message, metadata=payload.metadata)
    session = session_manager.add_message(session_id, user_message)

    stripped_message = payload.message.strip()
    indices = settings.indices

    if stripped_message.startswith("/lab"):
        lab_arg = stripped_message.split(maxsplit=1)
        requested_concept = lab_arg[1].strip() if len(lab_arg) == 2 else None
        if not requested_concept:
            if session.phase == "learning" and session.tuning_plan:
                requested_concept = session.tuning_plan[session.current_concept_index]["concept_name"]
            else:
                requested_concept = session.goal

        lab_payload = lab_primer.generate(requested_concept, session.goal)
        log_flow(
            "rag-orchestrator",
            "lab_primer.generated",
            "RAG orchestrator generated a lab primer package for the requested concept.",
            session_id=session_id,
            requested_concept=requested_concept,
            files=sorted([name for name in lab_payload.keys() if name != "summary"]),
        )
        summary = lab_payload.pop("summary")
        code_blocks = []
        for filename, content in lab_payload.items():
            fence = "yaml" if filename.endswith(".yml") or filename.endswith(".yaml") else "makefile" if filename.lower() == "makefile" else "markdown" if filename.endswith(".md") else "text"
            code_blocks.append(
                "\n".join([
                    f"```{fence}",
                    f"# {filename}",
                    content,
                    "```",
                ])
            )
        response_body = "\n\n".join([summary] + code_blocks)

        await elastic_client.store_interaction(
            index=indices["session_interactions"],
            session_id=session_id,
            role="user",
            content=payload.message,
            turn=session.current_turn(),
            embedding=None,
            metadata={**(payload.metadata or {}), "command": "lab"},
            phase=session.phase,
        )

        assistant_message = Message(
            role="assistant",
            content=response_body,
            metadata={"phase": session.phase, "stage": "lab_primer", "lab_concept": requested_concept},
        )
        session = session_manager.add_message(session_id, assistant_message)

        await elastic_client.store_interaction(
            index=indices["session_interactions"],
            session_id=session_id,
            role="assistant",
            content=assistant_message.content,
            turn=session.current_turn(),
            metadata=assistant_message.metadata,
            phase=session.phase,
        )
        updated_session = session_manager.get_session(session_id)
        await session_store.save(updated_session)
        log_flow(
            "rag-orchestrator",
            "api.sessions.message.completed",
            "RAG orchestrator finished the /lab branch and returned the generated lab primer.",
            session_id=session_id,
            phase=updated_session.phase,
            stage=assistant_message.metadata.get("stage"),
        )
        return SessionMessageResponse(
            session=_serialize_session(updated_session),
            last_message=_serialize_message(assistant_message),
        )

    embedding = await embedding_client.embed(payload.message)
    await elastic_client.store_interaction(
        index=indices["session_interactions"],
        session_id=session_id,
        role="user",
        content=payload.message,
        turn=session.current_turn(),
        embedding=embedding,
        metadata=payload.metadata,
        phase=session.phase,
    )

    # Handle based on current phase
    if session.phase in {"calibration", "tuning"}:
        log_flow(
            "rag-orchestrator",
            "calibration.processing",
            "RAG orchestrator is processing the learner answer inside the calibration or tuning branch.",
            session_id=session_id,
            phase=session.phase,
        )
        session_manager.record_calibration_answer(session_id, payload.message)

        calibration_history = session.calibration_history
        if calibration_history:
            latest = calibration_history[-1]
            if latest.get("answer"):
                planner = CalibrationPlanner(goal=session.goal, profile=session.profile)
                snapshot = planner.synthesize_snapshot(latest["question"], latest["answer"])
                await elastic_client.store_snapshot(
                    index=indices["knowledge_snapshots"],
                    session_id=session_id,
                    snapshot=snapshot,
                    embedding=embedding,
                )
                log_flow(
                    "rag-orchestrator",
                    "calibration.snapshot.created",
                    "RAG orchestrator synthesized a knowledge snapshot from the latest calibration answer.",
                    session_id=session_id,
                    question=latest["question"],
                )

        next_question = session_manager.next_calibration_question(session_id)

        if next_question:
            assistant_message = Message(
                role="assistant",
                content=next_question,
                metadata={"phase": session.phase, "stage": "calibration"},
            )
            session = session_manager.add_message(session_id, assistant_message)
            log_flow(
                "rag-orchestrator",
                "calibration.next_question",
                "RAG orchestrator asked the next calibration question.",
                session_id=session_id,
                question=assistant_message.content,
            )
        else:
            session = session_manager.get_session(session_id)
            generator = TuningProgramGenerator(
                goal=session.goal,
                calibration_history=session.calibration_history,
                external_resources=[],
            )
            search_query = generator.build_search_query()
            search_payload = await search_client.search(search_query, enrich=False)
            external_resources = _normalize_search_results(search_payload)
            log_flow(
                "rag-orchestrator",
                "search.resources.selected",
                "RAG orchestrator selected external search results for roadmap generation without inline page scraping to keep the learner request responsive.",
                session_id=session_id,
                search_query=search_query,
                external_resources=len(external_resources),
            )
            await _persist_learning_resources(
                elastic_client=elastic_client,
                embedding_client=embedding_client,
                index=indices["learning_resources"],
                session_id=session_id,
                resources=external_resources,
                extra_tags=[session.goal, "search", "calibration"],
            )
            generator = TuningProgramGenerator(
                goal=session.goal,
                calibration_history=session.calibration_history,
                external_resources=external_resources,
            )
            plan = await generator.generate(llm_client)
            session = session_manager.set_tuning_plan(session_id, plan)
            session = session_manager.begin_learning(session_id)

            for node in plan:
                await elastic_client.store_dependency_node(
                    index=indices["dependency_graph"],
                    node={**node, "session_id": session_id},
                )
                await _persist_learning_resources(
                    elastic_client=elastic_client,
                    embedding_client=embedding_client,
                    index=indices["learning_resources"],
                    session_id=session_id,
                    resources=node.get("resources", []),
                    concept_id=node.get("concept_id"),
                    extra_tags=[
                        session.goal,
                        node.get("concept_id", ""),
                        node.get("concept_name", ""),
                        "roadmap",
                    ],
                )

            summary_lines = [
                f"- {item['question']} → {item.get('answer', 'pending')}"
                for item in session.calibration_history
            ]
            coordinator = LearningCoordinator(plan=session.tuning_plan, index=session.current_concept_index)
            lesson_overview = coordinator.build_overview()
            summary = (
                "Calibration complete. Generated tuning roadmap with "
                f"{len(plan)} concepts. Here's what we've captured so far:\n" + "\n".join(summary_lines)
            )
            message_body = summary + "\n\n" + "**Next step: Phase 2 – Learning**\n" + lesson_overview
            assistant_message = Message(
                role="assistant",
                content=message_body,
                metadata={"phase": session.phase, "stage": "learning_intro", "concept_id": coordinator.current_node().get("concept_id")},
            )
            session = session_manager.add_message(session_id, assistant_message)
            log_flow(
                "rag-orchestrator",
                "learning.plan_ready",
                "RAG orchestrator finished calibration, generated the roadmap, and entered the learning phase.",
                session_id=session_id,
                concepts=len(plan),
                first_concept=coordinator.current_node().get("concept_id"),
                search_query=search_query,
                external_resources=len(external_resources),
            )

        await elastic_client.store_interaction(
            index=indices["session_interactions"],
            session_id=session_id,
            role="assistant",
            content=assistant_message.content,
            turn=session.current_turn(),
            metadata=assistant_message.metadata,
            phase=session.phase,
        )
    elif session.phase == "learning":
        plan = session.tuning_plan
        if not plan:
            raise HTTPException(status_code=400, detail="Learning plan not initialized")

        coordinator = LearningCoordinator(plan=plan, index=session.current_concept_index)
        concept = coordinator.current_node()
        log_flow(
            "rag-orchestrator",
            "learning.evaluation.started",
            "RAG orchestrator started evaluating the learner answer for the current learning concept.",
            session_id=session_id,
            concept_id=concept["concept_id"],
            concept_name=concept["concept_name"],
        )
        evaluation = await exercise_grader.evaluate(concept, payload.message)
        learning_status = "complete" if evaluation["passed"] else "needs_revision"
        session = session_manager.record_learning_outcome(
            session_id=session_id,
            concept_id=concept["concept_id"],
            status=learning_status,
            feedback=evaluation["feedback"],
        )

        await elastic_client.store_snapshot(
            index=indices["knowledge_snapshots"],
            session_id=session_id,
            snapshot={
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "status": learning_status,
                "feedback": evaluation["feedback"],
                "answer": payload.message,
                "score": evaluation.get("score"),
                "highlights": evaluation.get("highlights", []),
            },
            embedding=embedding if evaluation["passed"] else None,
        )
        log_flow(
            "rag-orchestrator",
            "learning.evaluation.completed",
            "RAG orchestrator finished evaluating the learner answer and persisted the concept snapshot.",
            session_id=session_id,
            concept_id=concept["concept_id"],
            passed=evaluation["passed"],
            score=evaluation.get("score"),
        )

        if evaluation["passed"]:
            session = session_manager.advance_concept(session_id)
            next_index = coordinator.next_index()
            if next_index is not None and session.phase != "learning_complete":
                coordinator = LearningCoordinator(plan=session.tuning_plan, index=session.current_concept_index)
                content = (
                    "Marked previous concept complete. Here's the next concept to focus on:\n\n" + coordinator.build_overview()
                )
                metadata = {
                    "phase": session.phase,
                    "stage": "learning_next",
                    "concept_id": coordinator.current_node()["concept_id"],
                    "score": evaluation.get("score"),
                }
            else:
                content = (
                    "Congratulations! You've completed all planned concepts. We'll capture a final summary next."
                )
                metadata = {"phase": session.phase, "stage": "learning_complete", "score": evaluation.get("score")}
        else:
            content = (
                evaluation["feedback"] + "\n\nRevise your answer considering the exercise criteria and resubmit when ready."
            )
            metadata = {
                "phase": session.phase,
                "stage": "learning_retry",
                "concept_id": concept["concept_id"],
                "score": evaluation.get("score"),
            }

        assistant_message = Message(
            role="assistant",
            content=content,
            metadata=metadata,
        )
        session = session_manager.add_message(session_id, assistant_message)

        await elastic_client.store_interaction(
            index=indices["session_interactions"],
            session_id=session_id,
            role="assistant",
            content=assistant_message.content,
            turn=session.current_turn(),
            metadata=assistant_message.metadata,
            phase=session.phase,
        )
    else:
        assistant_message = Message(
            role="assistant",
            content="Learning program already completed. Use /no more to wrap up or ask for a recap.",
            metadata={"phase": session.phase, "stage": "complete"},
        )
        session = session_manager.add_message(session_id, assistant_message)

        await elastic_client.store_interaction(
            index=indices["session_interactions"],
            session_id=session_id,
            role="assistant",
            content=assistant_message.content,
            turn=session.current_turn(),
            metadata=assistant_message.metadata,
            phase=session.phase,
        )

    updated_session = session_manager.get_session(session_id)
    await session_store.save(updated_session)
    log_flow(
        "rag-orchestrator",
        "api.sessions.message.completed",
        "RAG orchestrator finished processing the learner message and returned the assistant turn.",
        session_id=session_id,
        phase=updated_session.phase,
        stage=assistant_message.metadata.get("stage"),
    )

    return SessionMessageResponse(
        session=_serialize_session(updated_session),
        last_message=_serialize_message(assistant_message),
    )


@router.get("/{session_id}", response_model=SessionModel)
async def get_session(
    session_id: str,
    session_manager: SessionManagerDep,
    session_store: SessionStoreDep,
) -> SessionModel:
    log_flow(
        "rag-orchestrator",
        "api.sessions.show.received",
        "RAG orchestrator received a request to load a stored session by id.",
        session_id=session_id,
    )
    try:
        session = session_manager.get_session(session_id)
    except KeyError:
        stored = await session_store.get(session_id)
        if not stored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")
        session_manager.register_session(stored)
        session = stored
        log_flow(
            "rag-orchestrator",
            "api.sessions.show.restored",
            "RAG orchestrator restored the session from Elasticsearch for resume.",
            session_id=session_id,
            phase=session.phase,
        )

    log_flow(
        "rag-orchestrator",
        "api.sessions.show.completed",
        "RAG orchestrator returned the stored session payload.",
        session_id=session_id,
        phase=session.phase,
    )
    return _serialize_session(session)
