from __future__ import annotations

import asyncio
import json
from typing import Any

from ..clients.llm_client import LlmClient
from ..core.config import GradingProfile
from ..core.flow_logger import log_flow
from .exercise_grading_error import ExerciseGradingError
from .llm_generation_error import LlmGenerationError


class ExerciseGraderService:
    def __init__(self, llm_client: LlmClient, grading_profile: GradingProfile) -> None:
        self._llm = llm_client
        self._grading_profile = grading_profile

    async def evaluate(
        self,
        concept: dict[str, Any],
        answer: str,
    ) -> dict[str, Any]:
        prompt = self._build_prompt(concept, answer)
        log_flow(
            "rag-orchestrator",
            "grading.started",
            "ExerciseGraderService started evaluating the learner answer for the current concept.",
            concept_id=concept.get("concept_id"),
            concept_name=concept.get("concept_name"),
            answer=answer,
        )
        try:
            response = await asyncio.wait_for(
                self._llm.generate(
                    prompt,
                    system_prompt=(
                        "You are a strict technical mentor. "
                        "Return only valid JSON matching the requested schema."
                    ),
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=512,
                    request_timeout=25.0,
                ),
                timeout=25.0,
            )
            response_text = response.get("text") or ""
            result = self._parse_result(response_text)
            log_flow(
                "rag-orchestrator",
                "grading.llm_result",
                "ExerciseGraderService parsed a structured grading result from the LLM output.",
                concept_id=concept.get("concept_id"),
                passed=result.get("passed"),
                score=result.get("score"),
            )
            return result
        except TimeoutError as exc:
            raise ExerciseGradingError("Exercise grading timed out.") from exc
        except LlmGenerationError as exc:
            raise ExerciseGradingError(
                "Exercise grading failed because the LLM engine did not return usable output."
            ) from exc

    def _build_prompt(self, concept: dict[str, Any], answer: str) -> str:
        rubric_lines = [
            f"- {rubric_item.get('id')}: weight {rubric_item.get('weight', 0)} -> {rubric_item.get('instructions')}"
            for rubric_item in self._grading_profile.rubric
        ]
        resources = concept.get("resources", [])
        resource_lines = [
            f"  * {resource.get('title')} ({resource.get('type')}): {resource.get('url')}"
            for resource in resources
        ] or ["  * None provided"]
        lines = [
            "You are an expert mentor evaluating a learner's answer.",
            "Evaluate the answer strictly according to the rubric and respond with concise JSON using the schema:",
            "{\"passed\": bool, \"score\": float, \"feedback\": string, \"highlights\": [string]}",
            "",
            "Context:",
            f"- Goal: {concept.get('goal', 'N/A')}",
            f"- Concept: {concept.get('concept_name')}",
            f"- Summary: {concept.get('summary')}",
            f"- Exercise: {concept.get('exercise')}",
            "- Resources:",
            *resource_lines,
            "",
            "Rubric:",
            *rubric_lines,
            "",
            "Learner answer:",
            answer.strip(),
            "",
            "Return only the JSON object. Do not include explanations outside the JSON.",
        ]
        return "\n".join(lines).strip()

    def _parse_result(self, text: str) -> dict[str, Any]:
        try:
            json_start = text.index("{")
            json_end = text.rindex("}") + 1
            result_document = json.loads(text[json_start:json_end])
        except Exception as exc:
            raise ExerciseGradingError(
                "Exercise grading returned invalid JSON."
            ) from exc

        if not isinstance(result_document, dict):
            raise ExerciseGradingError(
                "Exercise grading returned an invalid result structure."
            )

        passed = bool(result_document.get("passed"))
        try:
            score = float(result_document.get("score", 0.0))
        except (TypeError, ValueError) as exc:
            raise ExerciseGradingError(
                "Exercise grading returned an invalid score value."
            ) from exc
        if score < 0.0 or score > 1.0:
            raise ExerciseGradingError(
                "Exercise grading returned an out-of-range score value."
            )

        feedback = result_document.get("feedback")
        if not isinstance(feedback, str) or not feedback.strip():
            raise ExerciseGradingError(
                "Exercise grading returned invalid feedback."
            )

        highlights = result_document.get("highlights")
        if not isinstance(highlights, list):
            raise ExerciseGradingError(
                "Exercise grading returned invalid highlights."
            )

        normalized_highlights = []
        for highlight in highlights:
            if not isinstance(highlight, str) or not highlight.strip():
                raise ExerciseGradingError(
                    "Exercise grading returned invalid highlights."
                )
            normalized_highlights.append(highlight.strip())

        return {
            "passed": passed,
            "score": score,
            "feedback": feedback.strip(),
            "highlights": normalized_highlights,
        }
