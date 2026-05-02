from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status

from ...core.config import Settings, get_settings
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
    _ = embedding_client, search_client, llm_client  # reserved for future use

    session = session_manager.create_session(goal=payload.goal, profile=payload.profile)

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
    return _serialize_session(persisted_session)


@router.post("/{session_id}", response_model=SessionMessageResponse)
async def send_message(
    session_id: str,
    payload: SessionMessagePayload,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
    embedding_client: EmbeddingClientDep,
    elastic_client: ElasticClientDep,
    exercise_grader: ExerciseGraderDep,
    lab_primer: LabPrimerDep,
    session_store: SessionStoreDep,
) -> SessionMessageResponse:
    try:
        session = session_manager.get_session(session_id)
    except KeyError as exc:
        stored = await session_store.get(session_id)
        if not stored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        session_manager.register_session(stored)
        session = session_manager.get_session(session_id)

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

        next_question = session_manager.next_calibration_question(session_id)

        if next_question:
            assistant_message = Message(
                role="assistant",
                content=next_question,
                metadata={"phase": session.phase, "stage": "calibration"},
            )
            session = session_manager.add_message(session_id, assistant_message)
        else:
            session = session_manager.get_session(session_id)
            generator = TuningProgramGenerator(goal=session.goal, calibration_history=session.calibration_history)
            plan = generator.generate()
            session = session_manager.set_tuning_plan(session_id, plan)
            session = session_manager.begin_learning(session_id)

            for node in plan:
                await elastic_client.store_dependency_node(
                    index=indices["dependency_graph"],
                    node={**node, "session_id": session_id},
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
    try:
        session = session_manager.get_session(session_id)
    except KeyError:
        stored = await session_store.get(session_id)
        if not stored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")
        session_manager.register_session(stored)
        session = stored

    return _serialize_session(session)
