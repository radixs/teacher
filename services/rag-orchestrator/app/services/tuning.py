from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List

from ..clients.llm import LlmClient
from ..core.flow_logger import log_flow


DEFAULT_CURRICULUM = [
    {
        "concept_id": "foundations",
        "concept_name": "Elasticsearch Fundamentals",
        "summary": "Core architecture, indices, documents, inverted index, querying basics.",
        "prerequisites": [],
        "resources": [
            {"type": "doc", "title": "Elasticsearch 101", "url": "https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html"},
            {"type": "course", "title": "Elastic Certified Engineer Study", "url": "https://www.elastic.co/training/"}
        ],
        "exercise": "List three core Elasticsearch components and describe how they interact during ingestion and search."
    },
    {
        "concept_id": "relevance",
        "concept_name": "Search Relevance Essentials",
        "summary": "Understanding BM25, scoring, analyzers, boosting, query tuning.",
        "prerequisites": ["foundations"],
        "resources": [
            {"type": "doc", "title": "Search Relevance Tuning", "url": "https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-search.html"}
        ],
        "exercise": "Provide an example where you would tune relevance scoring and which parameters/analyzers you would adjust."
    },
    {
        "concept_id": "vector_search",
        "concept_name": "Vector Search & Hybrid Retrieval",
        "summary": "Dense embeddings, kNN APIs, hybrid scoring strategies.",
        "prerequisites": ["foundations"],
        "resources": [
            {"type": "doc", "title": "Approximate kNN", "url": "https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html"}
        ],
        "exercise": "Explain how you would measure vector search quality for your use case and what fallback strategies you would keep."
    },
    {
        "concept_id": "rag_systems",
        "concept_name": "RAG System Design",
        "summary": "Chunking, retrieval pipelines, context management, evaluation.",
        "prerequisites": ["vector_search", "relevance"],
        "resources": [
            {"type": "article", "title": "Building RAG with Elasticsearch", "url": "https://www.elastic.co/blog"}
        ],
        "exercise": "Outline a retrieval pipeline for your goal and identify where Elasticsearch adds the most value."
    },
    {
        "concept_id": "esre_practice",
        "concept_name": "ESRE Engineering Practice",
        "summary": "Experimentation, evaluation metrics, production hardening, automation.",
        "prerequisites": ["rag_systems"],
        "resources": [
            {"type": "guide", "title": "Elastic Relevance Engine", "url": "https://www.elastic.co/what-is/elasticsearch/relevance-engine"}
        ],
        "exercise": "Draft an experiment plan to evaluate ESRE improvements and how you would operationalize the learnings."
    },
]


@dataclass
class TuningProgramGenerator:
    goal: str
    calibration_history: List[Dict[str, Any]]
    external_resources: List[Dict[str, Any]] = field(default_factory=list)

    async def generate(self, llm_client: LlmClient | None = None) -> List[Dict[str, Any]]:
        if llm_client is not None:
            plan = await self._generate_with_llm(llm_client)
            if plan:
                return plan

        return self._adaptive_fallback()

    def build_search_query(self) -> str:
        query_parts = [
            "Elasticsearch",
            "RAG",
            "vector search",
            "embeddings",
            "tutorial",
            "roadmap",
        ]
        base_query = " ".join(part for part in query_parts if part)
        return self._truncate_query(base_query, limit=220)

    def _adaptive_fallback(self) -> List[Dict[str, Any]]:
        plan = []
        for node in DEFAULT_CURRICULUM:
            plan.append({
                **node,
                "goal": self.goal,
                "confidence": self._estimate_confidence(node["concept_id"]),
                "resources": self._merge_resources(node),
            })
        log_flow(
            "rag-orchestrator",
            "tuning.plan.fallback",
            "Adaptive fallback roadmap was used after LLM roadmap generation failed or returned invalid data.",
            goal=self.goal,
            concepts=len(plan),
        )
        return plan

    def _estimate_confidence(self, concept_id: str) -> float:
        # Very naive placeholder; will evolve with real analytics.
        score = 0.5
        for record in self.calibration_history:
            answer = (record.get("answer") or "").lower()
            if concept_id in record.get("question", "").lower():
                score = 0.3
            if concept_id in answer:
                score = 0.7
        return round(score, 2)

    async def _generate_with_llm(self, llm_client: LlmClient) -> List[Dict[str, Any]]:
        calibration_summary = [
            {
                "question": item.get("question"),
                "answer": item.get("answer"),
            }
            for item in self.calibration_history
        ]
        resource_summary = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "summary": item.get("summary"),
                "type": item.get("type"),
            }
            for item in self.external_resources[:8]
        ]

        prompt = "\n".join(
            [
                "Create a personalized technical learning roadmap as JSON.",
                f"Goal: {self.goal}",
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
                "Keep summaries and exercises concise.",
                "resources must be an array of 1 or 2 objects with title, url, and type.",
                "Concepts should be ordered from foundational to advanced.",
                "Prefer the provided external resources when relevant.",
            ]
        )

        try:
            response = await asyncio.wait_for(
                llm_client.generate(
                    prompt,
                    system_prompt=(
                        "You generate structured personalized engineering roadmaps. "
                        "Respond only with valid JSON."
                    ),
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=896,
                    request_timeout=45.0,
                ),
                timeout=45.0,
            )
        except TimeoutError:
            return []
        text = response.get("text") or ""
        try:
            payload = json.loads(text)
        except Exception:
            return []

        raw_plan = payload.get("plan") if isinstance(payload, dict) else payload
        if not isinstance(raw_plan, list):
            return []

        plan: List[Dict[str, Any]] = []
        for index, item in enumerate(raw_plan):
            if not isinstance(item, dict):
                continue
            concept_name = str(item.get("concept_name") or "").strip()
            concept_id = str(item.get("concept_id") or "").strip() or f"concept_{index + 1}"
            summary = str(item.get("summary") or "").strip()
            exercise = str(item.get("exercise") or "").strip()
            if not concept_name or not summary or not exercise:
                continue
            prerequisites = item.get("prerequisites") or []
            resources = self._normalize_resources(item.get("resources"))
            if not resources:
                resources = self._merge_resources(item)
            plan.append(
                {
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "summary": summary,
                    "prerequisites": [str(entry) for entry in prerequisites if str(entry).strip()],
                    "resources": resources,
                    "exercise": exercise,
                    "goal": self.goal,
                    "confidence": self._coerce_confidence(item.get("confidence"), concept_id),
                }
            )

        if len(plan) < 3:
            return []

        log_flow(
            "rag-orchestrator",
            "tuning.plan.generated",
            "LLM generated a personalized roadmap using calibration answers and external resources.",
            goal=self.goal,
            concepts=len(plan),
            external_resources=len(self.external_resources),
        )
        return plan

    def _merge_resources(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        resources = self._normalize_resources(node.get("resources"))
        concept_terms = self._concept_terms(node)
        matched = []
        for resource in self.external_resources:
            haystack = " ".join(
                [
                    str(resource.get("title") or ""),
                    str(resource.get("summary") or ""),
                    str(resource.get("content") or ""),
                ]
            ).lower()
            if any(term in haystack for term in concept_terms):
                matched.append(
                    {
                        "title": resource.get("title"),
                        "url": resource.get("url"),
                        "type": resource.get("type", "search_result"),
                    }
                )
        merged = resources + [item for item in matched if item not in resources]
        return merged[:4]

    @staticmethod
    def _normalize_resources(value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []
        resources: List[Dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            resource_type = str(item.get("type") or "reference").strip()
            if title and url:
                resources.append({"title": title, "url": url, "type": resource_type})
        return resources

    @staticmethod
    def _concept_terms(node: Dict[str, Any]) -> List[str]:
        terms = [
            str(node.get("concept_id") or "").replace("_", " ").lower(),
            str(node.get("concept_name") or "").lower(),
        ]
        return [term for term in terms if term]

    def _coerce_confidence(self, value: Any, concept_id: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return self._estimate_confidence(concept_id)

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
