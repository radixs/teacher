from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GradingProfile:
    rubric: list[dict[str, Any]]
    pass_threshold: float
    retry_feedback: str
    pass_feedback: str

    @classmethod
    def from_dict(cls, grading_profile_document: dict[str, Any]) -> "GradingProfile":
        return cls(
            rubric=grading_profile_document.get("rubric", []),
            pass_threshold=float(grading_profile_document.get("pass_threshold", 0.6)),
            retry_feedback=grading_profile_document.get("retry_feedback", ""),
            pass_feedback=grading_profile_document.get("pass_feedback", "Great work."),
        )

