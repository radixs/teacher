from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class Message:
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] | None = None


@dataclass
class Session:
    id: str
    goal: str
    profile: dict[str, Any] | None = None
    phase: str = "calibration"
    messages: List[Message] = field(default_factory=list)
    calibration_queue: List[str] = field(default_factory=list)
    calibration_history: List[dict[str, Any]] = field(default_factory=list)
    tuning_plan: List[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def append(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def current_turn(self) -> int:
        return len(self.messages)
