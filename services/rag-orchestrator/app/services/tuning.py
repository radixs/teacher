from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


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

    def generate(self) -> List[Dict[str, Any]]:
        # TODO: incorporate calibration signal to re-rank or filter modules
        plan = []
        for node in DEFAULT_CURRICULUM:
            plan.append({
                **node,
                "goal": self.goal,
                "confidence": self._estimate_confidence(node["concept_id"]),
            })
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
