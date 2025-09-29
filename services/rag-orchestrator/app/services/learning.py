from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, List


@dataclass
class LearningCoordinator:
    plan: List[Dict[str, Any]]
    index: int

    def current_node(self) -> Dict[str, Any]:
        return self.plan[self.index]

    def build_overview(self) -> str:
        node = self.current_node()
        resources = "\n".join(
            f"  - [{item.get('title')} - {item.get('type')}]({item.get('url')})"
            for item in node.get("resources", [])
        ) or "  - No resources registered yet."

        exercise_prompt = dedent(
            node.get(
                "exercise",
                "Summarize what you learned from the resources above and outline a mini-experiment you could run to validate the concept.",
            )
        ).strip()

        return dedent(
            f"""
            **Concept:** {node.get('concept_name')}
            **Summary:** {node.get('summary')}
            **Why it matters:** Focus on how this unlocks later topics: {', '.join(node.get('prerequisites', []) or ['none'])}.

            **Resources to review:**
            {resources}

            **Exercise:** {exercise_prompt}
            When you are ready, send your answer describing what you learned and the steps you would take.
            """
        ).strip()

    def next_index(self) -> int | None:
        return self.index + 1 if self.index + 1 < len(self.plan) else None
