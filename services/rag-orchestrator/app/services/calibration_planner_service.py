from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from ..clients.llm_client import LlmClient
from ..core.config import (
    CalibrationPlannerConfig,
    get_calibration_planner_config,
)
from ..core.flow_logger import log_flow
from .calibration_question_generation_error import (
    CalibrationQuestionGenerationError,
)
from .llm_generation_error import LlmGenerationError


@dataclass
class CalibrationPlannerService:
    goal: str
    profile: dict[str, Any] | None = None
    calibration_planner_config: CalibrationPlannerConfig | None = None

    async def questions(self, llm_client: LlmClient | None = None) -> list[str]:
        if llm_client is None:
            raise CalibrationQuestionGenerationError(
                "Calibration question generation requires a working LLM client."
            )
        return await self._questions_from_llm(llm_client)

    def synthesize_snapshot(self, question: str, answer: str) -> dict[str, str]:
        return {
            "question": question,
            "answer": answer,
            "goal": self.goal,
        }

    async def _questions_from_llm(self, llm_client: LlmClient) -> list[str]:
        calibration_planner_config = self._config()
        profile_summary = str((self.profile or {}).get("summary") or "")
        prompt = calibration_planner_config.build_prompt(self.goal, profile_summary)
        try:
            response = await asyncio.wait_for(
                llm_client.generate(
                    prompt,
                    system_prompt=calibration_planner_config.system_prompt,
                    response_format={
                        "type": calibration_planner_config.response_format_type
                    },
                    temperature=calibration_planner_config.temperature,
                    max_tokens=calibration_planner_config.max_tokens,
                    request_timeout=calibration_planner_config.request_timeout,
                ),
                timeout=calibration_planner_config.timeout_seconds,
            )
        except TimeoutError as exc:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.failed",
                "LLM question generation exceeded the calibration time budget and the orchestrator will stop session creation.",
                goal=self.goal,
            )
            raise CalibrationQuestionGenerationError(
                "Calibration question generation timed out."
            ) from exc
        except LlmGenerationError as exc:
            raise CalibrationQuestionGenerationError(
                "Calibration question generation failed because the LLM engine did not return usable output."
            ) from exc

        response_text = response.get("text") or ""
        try:
            questions_document = self._parse_questions_document(response_text)
        except Exception as exc:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.failed",
                "LLM question generation returned invalid JSON and the orchestrator will stop session creation.",
                goal=self.goal,
            )
            raise CalibrationQuestionGenerationError(
                "Calibration question generation returned invalid JSON."
            ) from exc

        raw_questions = (
            questions_document.get("questions")
            if isinstance(questions_document, dict)
            else questions_document
        )
        if not isinstance(raw_questions, list):
            raise CalibrationQuestionGenerationError(
                "Calibration question generation returned an invalid questions structure."
            )

        unique_questions: list[str] = []
        for raw_question in raw_questions:
            question = self._coerce_question_text(raw_question)
            if question and question not in unique_questions:
                unique_questions.append(question)

        if len(unique_questions) < calibration_planner_config.minimum_usable_questions:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.failed",
                "LLM question generation produced too few usable questions and the orchestrator will stop session creation.",
                goal=self.goal,
                count=len(unique_questions),
            )
            raise CalibrationQuestionGenerationError(
                "Calibration question generation produced too few usable questions."
            )

        final_questions = unique_questions[: calibration_planner_config.question_count]
        log_flow(
            "rag-orchestrator",
            "calibration.questions.generated",
            "LLM generated the calibration question set for the new session.",
            goal=self.goal,
            count=len(final_questions),
        )
        return final_questions

    def _config(self) -> CalibrationPlannerConfig:
        return self.calibration_planner_config or get_calibration_planner_config()

    @staticmethod
    def _coerce_question_text(raw_question: Any) -> str:
        if isinstance(raw_question, str):
            return raw_question.strip()

        if isinstance(raw_question, dict):
            raw_question_text = raw_question.get("question")
            if isinstance(raw_question_text, str):
                return raw_question_text.strip()

        return ""

    @staticmethod
    def _parse_questions_document(response_text: str) -> Any:
        normalized_response_text = response_text.strip()

        if normalized_response_text.startswith("```"):
            normalized_response_text = CalibrationPlannerService._strip_code_fence(
                normalized_response_text
            )

        try:
            return json.loads(normalized_response_text)
        except json.JSONDecodeError:
            json_candidate_start_index = min(
                [
                    index
                    for index in [
                        normalized_response_text.find("{"),
                        normalized_response_text.find("["),
                    ]
                    if index >= 0
                ],
                default=-1,
            )
            if json_candidate_start_index >= 0:
                json_candidate = normalized_response_text[json_candidate_start_index:]
                questions_document, _ = json.JSONDecoder().raw_decode(json_candidate)
                return questions_document
            raise

    @staticmethod
    def _strip_code_fence(response_text: str) -> str:
        lines = response_text.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1]).strip()
        return response_text
