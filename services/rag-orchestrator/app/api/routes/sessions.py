from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.config import Settings, get_settings
from ...core.dependencies import (
    get_elasticsearch_client,
    get_embedding_client,
    get_llm_client,
    get_search_client,
    get_session_manager,
)
from ...models.api import (
    MessageModel,
    SessionMessageRequest,
    SessionMessageResponse,
    SessionModel,
    SessionStartRequest,
)
from ...models.session import Message
from ...services.calibration import CalibrationPlanner
from ...services.tuning import TuningProgramGenerator
from ...services.session_manager import SessionManager

router = APIRouter(prefix="/sessions", tags=["sessions"])


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
    payload: SessionStartRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    settings: Settings = Depends(get_settings),
    elastic_client=Depends(get_elasticsearch_client),
    embedding_client=Depends(get_embedding_client),
    search_client=Depends(get_search_client),
    llm_client=Depends(get_llm_client),  # kept for future orchestration hooks
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

    # Persist assistant prompt without embedding
    indices = settings.elasticsearch["indices"]
    await elastic_client.store_interaction(
        index=indices["session_interactions"],
        session_id=session.id,
        role="assistant",
        content=assistant_message.content,
        turn=session.current_turn(),
        metadata=assistant_message.metadata,
        phase=session.phase,
    )

    return _serialize_session(session_manager.get_session(session.id))


@router.post("/{session_id}", response_model=SessionMessageResponse)
async def send_message(
    session_id: str,
    payload: SessionMessageRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    settings: Settings = Depends(get_settings),
    embedding_client=Depends(get_embedding_client),
    elastic_client=Depends(get_elasticsearch_client),
) -> SessionMessageResponse:
    try:
        session = session_manager.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    user_message = Message(role="user", content=payload.message, metadata=payload.metadata)
    session = session_manager.add_message(session_id, user_message)

    embedding = await embedding_client.embed(payload.message)
    indices = settings.elasticsearch["indices"]
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
    else:
        session = session_manager.get_session(session_id)
        generator = TuningProgramGenerator(goal=session.goal, calibration_history=session.calibration_history)
        plan = generator.generate()
        session = session_manager.set_tuning_plan(session_id, plan)

        for node in plan:
            await elastic_client.store_dependency_node(
                index=indices["dependency_graph"],
                node={**node, "session_id": session_id},
            )

        summary_lines = [
            f"- {item['question']} → {item.get('answer', 'pending')}"
            for item in session.calibration_history
        ]
        summary = (
            "Calibration complete. Generated tuning roadmap with "
            f"{len(plan)} concepts. Here's what we've captured so far:
" + "
".join(summary_lines)
        )
        assistant_message = Message(
            role="assistant",
            content=summary,
            metadata={"phase": session.phase, "stage": "tuning_ready"},
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

    return SessionMessageResponse(
        session=_serialize_session(updated_session),
        last_message=_serialize_message(assistant_message),
    )



@router.get("/{session_id}", response_model=SessionModel)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionModel:
    try:
        session = session_manager.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _serialize_session(session)
