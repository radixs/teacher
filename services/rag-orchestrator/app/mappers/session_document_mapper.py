from __future__ import annotations

from datetime import datetime

from ..models.session_model import SessionModel
from .message_document_mapper import (
    deserialize_message_document,
    serialize_message_model,
)


def serialize_session_model(session_model: SessionModel) -> dict:
    return {
        "id": session_model.id,
        "goal": session_model.goal,
        "profile": session_model.profile or {},
        "phase": session_model.phase,
        "messages": [
            serialize_message_model(message_model)
            for message_model in session_model.messages
        ],
        "calibration_queue": session_model.calibration_queue,
        "calibration_history": session_model.calibration_history,
        "tuning_plan": session_model.tuning_plan,
        "current_concept_index": session_model.current_concept_index,
        "learning_progress": session_model.learning_progress,
        "created_at": session_model.created_at.isoformat(),
        "updated_at": session_model.updated_at.isoformat(),
    }


def deserialize_session_document(session_document: dict) -> SessionModel:
    created_at = session_document.get("created_at")
    updated_at = session_document.get("updated_at")
    return SessionModel(
        id=session_document["id"],
        goal=session_document.get("goal", ""),
        profile=session_document.get("profile") or {},
        phase=session_document.get("phase", "calibration"),
        messages=[
            deserialize_message_document(message_document)
            for message_document in session_document.get("messages", [])
        ],
        calibration_queue=list(session_document.get("calibration_queue", [])),
        calibration_history=list(session_document.get("calibration_history", [])),
        tuning_plan=list(session_document.get("tuning_plan", [])),
        current_concept_index=int(session_document.get("current_concept_index", 0)),
        learning_progress=list(session_document.get("learning_progress", [])),
        created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow(),
        updated_at=datetime.fromisoformat(updated_at) if updated_at else datetime.utcnow(),
    )

