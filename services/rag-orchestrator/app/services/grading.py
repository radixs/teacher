from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..clients.llm import LlmClient


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
        try:
            response = await self._llm.generate(prompt)
            text = response.get("content") or response.get("text") or ""
            result = self._parse_result(text)
        except Exception:
            result = None

        if not result:
            result = self._heuristic_fallback(answer)

        return result

    def _build_prompt(self, concept: Dict[str, Any], answer: str) -> str:
        rubric_lines = []
        for item in self._profile.rubric:
            rubric_lines.append(
                f"- {item.get('id')}: weight {item.get('weight', 0)} -> {item.get('instructions')}"
            )

        resources = concept.get("resources", [])
        resource_lines = [
            f"  * {res.get('title')} ({res.get('type')}): {res.get('url')}"
            for res in resources
        ] or ["  * None provided"]

        prompt = f"""
You are an expert mentor evaluating a learner's answer.
Evaluate the answer strictly according to the rubric and respond with concise JSON using the schema:
{{"passed": bool, "score": float, "feedback": string, "highlights": [string]}}

Context:
- Goal: {concept.get('goal', 'N/A')}
- Concept: {concept.get('concept_name')}
- Summary: {concept.get('summary')}
- Exercise: {concept.get('exercise')}
- Resources:\n{chr(10).join(resource_lines)}

Rubric:
{chr(10).join(rubric_lines)}

Learner answer:
"""{answer}"""

Return only the JSON object. Do not include explanations outside the JSON.
"""
        return prompt.strip()

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
