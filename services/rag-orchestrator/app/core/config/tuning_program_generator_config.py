from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from typing import Any


@dataclass(frozen=True)
class TuningProgramGeneratorConfig:
    search_query_parts: list[str] = field(
        default_factory=lambda: [
            "Elasticsearch",
            "RAG",
            "vector search",
            "embeddings",
            "tutorial",
            "roadmap",
        ]
    )
    search_query_limit: int = 220
    system_prompt: str = (
        "You generate structured personalized engineering roadmaps. "
        "Respond only with valid JSON."
    )
    response_format_type: str = "json_object"
    temperature: float = 0.1
    max_tokens: int = 3000
    request_timeout: float = 120.0
    timeout_seconds: float = 120.0
    minimum_plan_items: int = 3

    def build_prompt(
        self,
        goal: str,
        calibration_summary: list[dict[str, Any]],
        resource_summary: list[dict[str, Any]],
    ) -> str:
        return "\n".join(
            [
                "Create a personalized technical learning roadmap as JSON.",
                f"Goal: {goal}",
                "",
                "Calibration answers:",
                json.dumps(calibration_summary, ensure_ascii=True),
                "",
                "External learning resources:",
                json.dumps(resource_summary, ensure_ascii=True),
                "",
                "Return a JSON object with a top-level key named plan.",
                "plan must be an array of exactly 4 roadmap items.",
                "Each roadmap item must contain concept_id, concept_name, summary, prerequisites, resources, exercise, confidence.",
                "Use those exact snake_case field names. Do not rename exercise to task, project, assignment, or practical_exercise.",
                "Keep summaries and exercises concise.",
                "resources must be an array of 1 or 2 objects with title, url, and type.",
                "Concepts should be ordered from foundational to advanced.",
                "Prefer the provided external resources when relevant.",
            ]
        )


@lru_cache()
def get_tuning_program_generator_config() -> TuningProgramGeneratorConfig:
    return TuningProgramGeneratorConfig()
