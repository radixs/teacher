from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.config import Settings, get_settings
from ...core.dependencies import (
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
    )


@router.post("", response_model=SessionModel)
async def start_session(
    payload: SessionStartRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    settings: Settings = Depends(get_settings),
    llm_client=Depends(get_llm_client),
    embedding_client=Depends(get_embedding_client),
    search_client=Depends(get_search_client),
) -> SessionModel:
    # TODO: leverage embedding_client and search_client to prime session context.
    _ = embedding_client, search_client, settings
    session = session_manager.create_session(goal=payload.goal, profile=payload.profile)

    llm_response = await llm_client.generate(
        prompt=(
            "The user wants to learn {goal}. Start calibration with a single welcoming question."
        ).format(goal=payload.goal)
    )

    content = llm_response.get("content") or llm_response.get("text") or "Welcome! Let's begin by clarifying what you already know about this goal."
    assistant_message = Message(
        role="assistant",
        content=content,
        metadata={"phase": session.phase},
    )
    session_manager.add_message(session.id, assistant_message)

    return _serialize_session(session_manager.get_session(session.id))


@router.post("/{session_id}", response_model=SessionMessageResponse)
async def send_message(
    session_id: str,
    payload: SessionMessageRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    llm_client=Depends(get_llm_client),
) -> SessionMessageResponse:
    try:
        session = session_manager.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    user_message = Message(role="user", content=payload.message, metadata=payload.metadata)
    session_manager.add_message(session_id, user_message)

    llm_response = await llm_client.generate(
        prompt=payload.message,
        context={
            "phase": session.phase,
            "messages": [msg.__dict__ for msg in session.messages],
        },
    )

    content = llm_response.get("content") or llm_response.get("text") or "Acknowledged. Further orchestration logic will arrive in a later step."
    assistant_message = Message(
        role="assistant",
        content=content,
        metadata={"phase": session.phase},
    )
    session_manager.add_message(session_id, assistant_message)

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
