from __future__ import annotations

from datetime import datetime

from ..models.message_model import MessageModel


def serialize_message_model(message_model: MessageModel) -> dict:
    return {
        "role": message_model.role,
        "content": message_model.content,
        "created_at": message_model.created_at.isoformat(),
        "metadata": message_model.metadata or {},
    }


def deserialize_message_document(message_document: dict) -> MessageModel:
    created_at = message_document.get("created_at")
    timestamp = datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
    return MessageModel(
        role=message_document.get("role", "assistant"),
        content=message_document.get("content", ""),
        created_at=timestamp,
        metadata=message_document.get("metadata") or {},
    )

