from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def append(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
