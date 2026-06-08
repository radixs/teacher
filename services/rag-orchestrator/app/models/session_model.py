from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .message_model import MessageModel


@dataclass
class SessionModel:
    id: str
    goal: str
    profile: dict[str, Any] | None = None
    phase: str = "calibration"
    messages: list[MessageModel] = field(default_factory=list)
    calibration_queue: list[str] = field(default_factory=list)
    calibration_history: list[dict[str, Any]] = field(default_factory=list)
    tuning_plan: list[dict[str, Any]] = field(default_factory=list)
    current_concept_index: int = 0
    learning_progress: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def append(self, message_model: MessageModel) -> None:
        self.messages.append(message_model)
        self.updated_at = datetime.utcnow()

    def current_turn(self) -> int:
        return len(self.messages)

