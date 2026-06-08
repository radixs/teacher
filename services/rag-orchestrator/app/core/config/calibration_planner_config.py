from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class CalibrationPlannerConfig:
    system_prompt: str = (
        "You design calibration questions for an engineering learning mentor. "
        "Respond only with valid JSON."
    )
    response_format_type: str = "json_object"
    temperature: float = 0.1
    max_tokens: int = 384
    request_timeout: float = 25.0
    timeout_seconds: float = 25.0
    question_count: int = 6
    minimum_usable_questions: int = 4

    def build_prompt(self, goal: str, profile_summary: str) -> str:
        return "\n".join(
            [
                "Create 6 calibration questions for a personalized technical learning program.",
                f"Learning goal: {goal}",
                f"Learner background summary: {profile_summary or 'None provided'}",
                "",
                "Return a JSON object with exactly one key named questions.",
                "The value must be an array of 6 short, concrete questions.",
                "Questions should assess prior knowledge, hands-on experience, target outcome, tooling baseline, and knowledge gaps.",
                "Do not ask about weekly time commitment, schedules, or hours available.",
            ]
        )


@lru_cache()
def get_calibration_planner_config() -> CalibrationPlannerConfig:
    return CalibrationPlannerConfig()
