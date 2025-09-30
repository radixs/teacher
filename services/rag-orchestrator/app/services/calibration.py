from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


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

    def questions(self) -> List[str]:
        # Future enhancement: tailor questions using goal/profile + LLM
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
