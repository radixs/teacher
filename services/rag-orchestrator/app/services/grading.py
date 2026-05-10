from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..clients.llm import LlmClient
from ..core.flow_logger import log_flow


@dataclass
class GradingProfile:
    rubric: List[Dict[str, Any]]
    pass_threshold: float
    retry_feedback: str
    pass_feedback: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GradingProfile":
        return cls(
            rubric=data.get("rubric", []),
            pass_threshold=float(data.get("pass_threshold", 0.6)),
            retry_feedback=data.get("retry_feedback", ""),
            pass_feedback=data.get("pass_feedback", "Great work."),
        )


class GradingConfig:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Grading config not found at {self._path}")
        with self._path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        self.profiles: Dict[str, GradingProfile] = {
            name: GradingProfile.from_dict(profile)
            for name, profile in (payload.get("profiles") or {}).items()
        }

    def get(self, name: str) -> GradingProfile:
        if name not in self.profiles:
            raise KeyError(f"Grading profile '{name}' not defined")
        return self.profiles[name]


class ExerciseGrader:
    def __init__(self, llm_client: LlmClient, profile: GradingProfile) -> None:
        self._llm = llm_client
        self._profile = profile

    async def evaluate(
        self,
        concept: Dict[str, Any],
        answer: str,
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(concept, answer)
        log_flow(
            "rag-orchestrator",
            "grading.started",
            "ExerciseGrader started evaluating the learner answer for the current concept.",
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
            text = response.get("content") or response.get("text") or ""
            result = self._parse_result(text)
            if result:
                log_flow(
                    "rag-orchestrator",
                    "grading.llm_result",
                    "ExerciseGrader parsed a structured grading result from the LLM output.",
                    concept_id=concept.get("concept_id"),
                    passed=result.get("passed"),
                    score=result.get("score"),
                )
        except Exception:
            result = None

        if not result:
            result = self._heuristic_fallback(answer)
            log_flow(
                "rag-orchestrator",
                "grading.heuristic_fallback",
                "ExerciseGrader fell back to the local heuristic scoring path.",
                passed=result.get("passed"),
                score=result.get("score"),
            )

        return result

    def _build_prompt(self, concept: Dict[str, Any], answer: str) -> str:
        rubric_lines = [
            f"- {item.get('id')}: weight {item.get('weight', 0)} -> {item.get('instructions')}"
            for item in self._profile.rubric
        ]

        resources = concept.get("resources", [])
        resource_lines = [
            f"  * {res.get('title')} ({res.get('type')}): {res.get('url')}"
            for res in resources
        ] or ["  * None provided"]

        lines = [
            "You are an expert mentor evaluating a learner's answer.",
            "Evaluate the answer strictly according to the rubric and respond with concise JSON using the schema:",
            "{\"passed\": bool, \"score\": float, \"feedback\": string, \"highlights\": [string]}",
            "",
            f"Context:",
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

        # Flatten nested lists that result from the unpacking above
        flattened: list[str] = []
        for entry in lines:
            if isinstance(entry, list):
                flattened.extend(entry)
            else:
                flattened.append(entry)

        return "\n".join(flattened).strip()

    def _parse_result(self, text: str) -> Dict[str, Any] | None:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            data = json.loads(text[start:end])
        except Exception:
            return None

        passed = bool(data.get("passed"))
        score = float(data.get("score", 0.0))
        feedback = data.get("feedback") or (
            self._profile.pass_feedback if passed else self._profile.retry_feedback
        )
        highlights = data.get("highlights") or []
        return {
            "passed": passed,
            "score": max(0.0, min(score, 1.0)),
            "feedback": feedback,
            "highlights": highlights,
        }

    def _heuristic_fallback(self, answer: str) -> Dict[str, Any]:
        tokens = answer.strip().split()
        length_score = min(len(tokens) / 80.0, 1.0)
        contains_keywords = any(
            keyword in answer.lower()
            for keyword in ["experiment", "metric", "evaluate", "index", "vector"]
        )
        score = 0.7 * length_score + (0.3 if contains_keywords else 0.0)
        passed = score >= self._profile.pass_threshold
        feedback = (
            self._profile.pass_feedback if passed else self._profile.retry_feedback
        )
        return {
            "passed": passed,
            "score": round(score, 2),
            "feedback": feedback,
            "highlights": [],
        }


def load_grading_config(path: str) -> GradingConfig:
    return GradingConfig(path)
