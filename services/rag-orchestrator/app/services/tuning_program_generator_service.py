from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from ..clients.llm_client import LlmClient
from ..core.config import (
    TuningProgramGeneratorConfig,
    get_tuning_program_generator_config,
)
from ..core.flow_logger import log_flow
from .llm_generation_error import LlmGenerationError
from .tuning_plan_generation_error import TuningPlanGenerationError


@dataclass
class TuningProgramGeneratorService:
    goal: str
    calibration_history: list[dict[str, Any]]
    external_resources: list[dict[str, Any]] = field(default_factory=list)
    tuning_program_generator_config: TuningProgramGeneratorConfig | None = None

    async def generate(self, llm_client: LlmClient | None = None) -> list[dict[str, Any]]:
        if llm_client is None:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation requires a working LLM client."
            )
        return await self._generate_with_llm(llm_client)

    def build_search_query(self) -> str:
        tuning_program_generator_config = self._config()
        base_query = " ".join(
            query_part
            for query_part in tuning_program_generator_config.search_query_parts
            if query_part
        )
        return self._truncate_query(
            base_query,
            limit=tuning_program_generator_config.search_query_limit,
        )

    async def _generate_with_llm(self, llm_client: LlmClient) -> list[dict[str, Any]]:
        tuning_program_generator_config = self._config()
        calibration_summary = [
            {
                "question": calibration_record.get("question"),
                "answer": calibration_record.get("answer"),
            }
            for calibration_record in self.calibration_history
        ]
        resource_summary = [
            {
                "title": external_resource.get("title"),
                "url": external_resource.get("url"),
                "summary": self._truncate_text(external_resource.get("summary"), limit=180),
                "type": external_resource.get("type"),
            }
            for external_resource in self.external_resources[:5]
        ]
        prompt = tuning_program_generator_config.build_prompt(
            self.goal,
            calibration_summary,
            resource_summary,
        )

        try:
            response = await asyncio.wait_for(
                llm_client.generate(
                    prompt,
                    system_prompt=tuning_program_generator_config.system_prompt,
                    response_format={
                        "type": tuning_program_generator_config.response_format_type
                    },
                    temperature=tuning_program_generator_config.temperature,
                    max_tokens=tuning_program_generator_config.max_tokens,
                    request_timeout=tuning_program_generator_config.request_timeout,
                ),
                timeout=tuning_program_generator_config.timeout_seconds,
            )
        except TimeoutError as exc:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation timed out."
            ) from exc
        except LlmGenerationError as exc:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation failed because the LLM engine did not return usable output."
            ) from exc

        response_text = response.get("text") or ""
        try:
            plan_document = self._parse_plan_document(response_text)
        except Exception as exc:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation returned invalid JSON."
            ) from exc

        raw_plan = plan_document.get("plan") if isinstance(plan_document, dict) else plan_document
        if not isinstance(raw_plan, list):
            raise TuningPlanGenerationError(
                "Tuning roadmap generation returned an invalid plan structure."
            )

        plan: list[dict[str, Any]] = []
        for index, plan_node in enumerate(raw_plan):
            if not isinstance(plan_node, dict):
                raise TuningPlanGenerationError(
                    "Tuning roadmap generation returned a non-object plan item."
                )
            concept_name = self._first_non_empty_string(
                plan_node,
                ["concept_name", "title", "name", "topic"],
            )
            concept_id = (
                self._first_non_empty_string(plan_node, ["concept_id", "id", "slug"])
                or f"concept_{index + 1}"
            )
            summary = self._first_non_empty_string(
                plan_node,
                ["summary", "description", "overview", "objective"],
            )
            exercise = self._first_non_empty_string(
                plan_node,
                [
                    "exercise",
                    "practical_exercise",
                    "hands_on_exercise",
                    "task",
                    "project",
                    "assignment",
                ],
            )
            if not concept_name or not summary or not exercise:
                log_flow(
                    "rag-orchestrator",
                    "tuning.plan.failed",
                    "A roadmap item was missing one or more required fields after alias normalization.",
                    goal=self.goal,
                    item_index=index,
                    keys=sorted(plan_node.keys()),
                )
                raise TuningPlanGenerationError(
                    "Tuning roadmap generation returned a plan item with missing required fields."
                )
            prerequisites = self._normalize_prerequisites(
                plan_node.get("prerequisites")
                or plan_node.get("depends_on")
                or plan_node.get("requirements")
            )
            if prerequisites is None:
                raise TuningPlanGenerationError(
                    "Tuning roadmap generation returned invalid prerequisites for a plan item."
                )
            resources = self._normalize_resources(plan_node.get("resources"))
            if not resources:
                raise TuningPlanGenerationError(
                    "Tuning roadmap generation returned a plan item without valid resources."
                )
            plan.append(
                {
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "summary": summary,
                    "prerequisites": [
                        str(entry) for entry in prerequisites if str(entry).strip()
                    ],
                    "resources": resources,
                    "exercise": exercise,
                    "goal": self.goal,
                    "confidence": self._parse_confidence(plan_node.get("confidence")),
                }
            )

        if len(plan) < tuning_program_generator_config.minimum_plan_items:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation produced too few usable plan items."
            )

        log_flow(
            "rag-orchestrator",
            "tuning.plan.generated",
            "LLM generated a personalized roadmap using calibration answers and external resources.",
            goal=self.goal,
            concepts=len(plan),
            external_resources=len(self.external_resources),
        )
        return plan

    @staticmethod
    def _normalize_resources(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        resources: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = TuningProgramGeneratorService._first_non_empty_string(
                item,
                ["title", "name", "label"],
            )
            url = TuningProgramGeneratorService._first_non_empty_string(
                item,
                ["url", "link", "href"],
            )
            resource_type = (
                TuningProgramGeneratorService._first_non_empty_string(
                    item,
                    ["type", "kind", "format"],
                )
                or "reference"
            )
            if title and url:
                resources.append({"title": title, "url": url, "type": resource_type})
        return resources

    @staticmethod
    def _normalize_prerequisites(value: Any) -> list[str] | None:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(entry) for entry in value if str(entry).strip()]
        if isinstance(value, str):
            normalized_value = value.strip()
            return [normalized_value] if normalized_value else []
        return None

    @staticmethod
    def _parse_confidence(value: Any) -> float:
        if isinstance(value, str):
            normalized_text = value.strip().lower()
            textual_confidence_map = {
                "very low": 0.2,
                "low": 0.35,
                "moderate": 0.6,
                "medium": 0.6,
                "medium-high": 0.72,
                "high": 0.8,
                "very high": 0.92,
            }
            if normalized_text in textual_confidence_map:
                return textual_confidence_map[normalized_text]
            if "/" in normalized_text:
                numerator_text, denominator_text = normalized_text.split("/", 1)
                try:
                    numerator = float(numerator_text.strip())
                    denominator = float(denominator_text.strip())
                except ValueError:
                    numerator = None
                    denominator = None
                if numerator is not None and denominator and denominator > 0.0:
                    confidence = numerator / denominator
                    if 0.0 <= confidence <= 1.0:
                        return confidence
            normalized_value = normalized_text.rstrip("%").strip().replace(",", ".")
        else:
            normalized_value = value
        try:
            confidence = float(normalized_value)
        except (TypeError, ValueError):
            raise TuningPlanGenerationError(
                "Tuning roadmap generation returned an invalid confidence value."
            ) from None
        if confidence > 1.0 and confidence <= 100.0:
            confidence = confidence / 100.0
        if confidence < 0.0 or confidence > 1.0:
            raise TuningPlanGenerationError(
                "Tuning roadmap generation returned an out-of-range confidence value."
            )
        return confidence

    @staticmethod
    def _truncate_query(query: str, *, limit: int) -> str:
        compact = " ".join(query.split())
        if len(compact) <= limit:
            return compact

        truncated = compact[:limit].rstrip()
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated.strip()

    def _config(self) -> TuningProgramGeneratorConfig:
        return self.tuning_program_generator_config or get_tuning_program_generator_config()

    @staticmethod
    def _parse_plan_document(response_text: str) -> Any:
        normalized_response_text = response_text.strip()

        if normalized_response_text.startswith("```"):
            normalized_response_text = TuningProgramGeneratorService._strip_code_fence(
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
                plan_document, _ = json.JSONDecoder().raw_decode(json_candidate)
                return plan_document
            raise

    @staticmethod
    def _strip_code_fence(response_text: str) -> str:
        lines = response_text.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1]).strip()
        return response_text

    @staticmethod
    def _truncate_text(value: Any, *, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    @staticmethod
    def _first_non_empty_string(source: dict[str, Any], keys: list[str]) -> str:
        for key in keys:
            value = source.get(key)
            if value is None:
                continue
            normalized_value = str(value).strip()
            if normalized_value:
                return normalized_value
        return ""
