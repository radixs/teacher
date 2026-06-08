from __future__ import annotations

from dataclasses import dataclass

from ..models.message_model import MessageModel
from ..models.session_model import SessionModel


@dataclass
class SessionMessageResult:
    session: SessionModel
    last_message: MessageModel

