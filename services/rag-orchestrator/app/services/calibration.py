from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..clients.llm import LlmClient
from ..core.flow_logger import log_flow


CALIBRATION_QUESTIONS = [
    "What prior experience do you have with Elasticsearch or search relevance?",
    "How comfortable are you describing how documents are indexed and retrieved in Elasticsearch?",
    "Do you have hands-on experience with embeddings or vector search concepts?",
    "Which programming languages and frameworks do you plan to use alongside ESRE work?",
    "What outcome are you aiming for in the next 4 weeks of learning?",
    "How much time per week can you dedicate to guided practice and labs?",
]


@dataclass
class CalibrationPlanner:
    goal: str
    profile: Optional[Dict[str, str]] = None

    async def questions(self, llm_client: LlmClient | None = None) -> List[str]:
        if llm_client is not None:
            questions = await self._questions_from_llm(llm_client)
            if questions:
                return questions

        return self._fallback_questions()

    def _fallback_questions(self) -> List[str]:
        base_questions = list(CALIBRATION_QUESTIONS)
        if self.profile and self.profile.get("summary"):
            base_questions.insert(0, "Summarize your current understanding of the goal in your own words.")
        return base_questions

    def synthesize_snapshot(self, question: str, answer: str) -> Dict[str, str]:
        return {
            "question": question,
            "answer": answer,
            "goal": self.goal,
        }

    async def _questions_from_llm(self, llm_client: LlmClient) -> List[str]:
        profile_summary = (self.profile or {}).get("summary", "")
        prompt = "\n".join(
            [
                "Create 6 calibration questions for a personalized technical learning program.",
                f"Learning goal: {self.goal}",
                f"Learner background summary: {profile_summary or 'None provided'}",
                "",
                "Return a JSON object with exactly one key named questions.",
                "The value must be an array of 6 short, concrete questions.",
                "Questions should assess prior knowledge, available time, hands-on experience, target outcome, and gaps.",
            ]
        )
        try:
            response = await asyncio.wait_for(
                llm_client.generate(
                    prompt,
                    system_prompt=(
                        "You design calibration questions for an engineering learning mentor. "
                        "Respond only with valid JSON."
                    ),
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=384,
                    request_timeout=25.0,
                ),
                timeout=25.0,
            )
        except TimeoutError:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.fallback",
                "LLM question generation exceeded the calibration time budget, so fallback questions were used.",
                goal=self.goal,
            )
            return []
        text = response.get("text") or ""
        try:
            payload = json.loads(text)
        except Exception:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.fallback",
                "LLM question generation returned invalid JSON, so fallback calibration questions were used.",
                goal=self.goal,
            )
            return []

        raw_questions = payload.get("questions") if isinstance(payload, dict) else payload
        if not isinstance(raw_questions, list):
            return []

        questions: List[str] = []
        for item in raw_questions:
            if not isinstance(item, str):
                continue
            question = item.strip()
            if question and question not in questions:
                questions.append(question)

        if len(questions) < 4:
            log_flow(
                "rag-orchestrator",
                "calibration.questions.fallback",
                "LLM question generation produced too few usable questions, so fallback questions were used.",
                goal=self.goal,
                count=len(questions),
            )
            return []

        final_questions = questions[:6]
        log_flow(
            "rag-orchestrator",
            "calibration.questions.generated",
            "LLM generated the calibration question set for the new session.",
            goal=self.goal,
            count=len(final_questions),
        )
        return final_questions
