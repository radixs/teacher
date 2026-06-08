from fastapi.testclient import TestClient

from app.main import app
from app.core.service_container import (
    get_elasticsearch_client,
    get_embedding_client,
    get_llm_client,
    get_search_client,
    get_session_manager_service,
    get_exercise_grader_service,
    get_session_repository,
    get_lab_primer_service,
)
from app.services.session_manager_service import SessionManagerService
from app.models.session_model import SessionModel
from app.services.exercise_grading_error import ExerciseGradingError
from app.services.external_search_error import ExternalSearchError


class FakeEmbeddingClient:
    async def embed(self, text: str):
        return [0.0, 0.1, 0.2]


class FakeLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    '{"plan": ['
                    '{'
                    '"concept_id":"foundations",'
                    '"concept_name":"Elasticsearch Foundations",'
                    '"summary":"Understand indices, documents, mappings, and query basics.",'
                    '"prerequisites":[],'
                    '"resources":[{"title":"Elastic Intro","url":"https://example.com/intro","type":"doc"}],'
                    '"exercise":"Explain index, shard, and document flow in your own words.",'
                    '"confidence":0.45'
                    '},'
                    '{'
                    '"concept_id":"relevance",'
                    '"concept_name":"Search Relevance Tuning",'
                    '"summary":"Understand analyzers, BM25, boosts, and evaluation signals.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Relevance Guide","url":"https://example.com/relevance-guide","type":"doc"}],'
                    '"exercise":"Describe how you would debug weak ranking for a known query.",'
                    '"confidence":0.58'
                    '},'
                    '{'
                    '"concept_id":"vector_search",'
                    '"concept_name":"Vector Search Practice",'
                    '"summary":"Learn embeddings, kNN, and hybrid retrieval design.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Hybrid Search Notes","url":"https://example.com/hybrid","type":"article"}],'
                    '"exercise":"Design a hybrid retrieval experiment for your use case.",'
                    '"confidence":0.62'
                    '},'
                    '{'
                    '"concept_id":"rag_systems",'
                    '"concept_name":"RAG Delivery Patterns",'
                    '"summary":"Combine storage, retrieval, prompting, and evaluation into a production flow.",'
                    '"prerequisites":["relevance","vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"exercise":"Outline a RAG architecture with retrieval, prompting, and feedback loops.",'
                    '"confidence":0.7'
                    '}'
                    ']}'
                )
            }
        return {"text": ""}


class FakeSearchClient:
    async def search(self, query: str, *, enrich: bool = False):
        return {
            "query": query,
            "results": [
                {
                    "title": "Search Relevance Guide",
                    "url": "https://example.com/relevance",
                    "snippet": "Practical relevance tuning for Elasticsearch systems.",
                    "content": "Relevance tuning covers analyzers, BM25, hybrid retrieval, and experiments.",
                },
                {
                    "title": "Vector Retrieval Notes",
                    "url": "https://example.com/vector",
                    "snippet": "Embeddings and vector search foundations.",
                    "content": "Vector retrieval works with embedding generation, kNN, and evaluation loops.",
                },
            ],
        }


class FailingSearchClient:
    async def search(self, query: str, *, enrich: bool = False):
        raise ExternalSearchError("Search agent failed to return search results.")


class FakeGrader:
    async def evaluate(self, concept, answer):
        return {
            "passed": True,
            "score": 0.9,
            "feedback": "Looks good.",
            "highlights": [concept.get("concept_name")],
        }


class FailingGrader:
    async def evaluate(self, concept, answer):
        raise ExerciseGradingError("Exercise grading failed for the current concept.")


class InvalidCalibrationLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        return {"text": "not valid json"}


class InvalidRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {"text": "not valid json"}
        return {"text": ""}


class WrappedRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    "```json\n"
                    '{"plan": ['
                    '{'
                    '"concept_id":"foundations",'
                    '"concept_name":"Elasticsearch Foundations",'
                    '"summary":"Understand indices, documents, mappings, and query basics.",'
                    '"prerequisites":[],'
                    '"resources":[{"title":"Elastic Intro","url":"https://example.com/intro","type":"doc"}],'
                    '"exercise":"Explain index, shard, and document flow in your own words.",'
                    '"confidence":0.45'
                    '},'
                    '{'
                    '"concept_id":"relevance",'
                    '"concept_name":"Search Relevance Tuning",'
                    '"summary":"Understand analyzers, BM25, boosts, and evaluation signals.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Relevance Guide","url":"https://example.com/relevance-guide","type":"doc"}],'
                    '"exercise":"Describe how you would debug weak ranking for a known query.",'
                    '"confidence":0.58'
                    '},'
                    '{'
                    '"concept_id":"vector_search",'
                    '"concept_name":"Vector Search Practice",'
                    '"summary":"Learn embeddings, kNN, and hybrid retrieval design.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Hybrid Search Notes","url":"https://example.com/hybrid","type":"article"}],'
                    '"exercise":"Design a hybrid retrieval experiment for your use case.",'
                    '"confidence":0.62'
                    '},'
                    '{'
                    '"concept_id":"rag_systems",'
                    '"concept_name":"RAG Delivery Patterns",'
                    '"summary":"Combine storage, retrieval, prompting, and evaluation into a production flow.",'
                    '"prerequisites":["relevance","vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"exercise":"Outline a RAG architecture with retrieval, prompting, and feedback loops.",'
                    '"confidence":0.7'
                    '}'
                    ']}\n'
                    "```"
                )
            }
        return {"text": ""}


class TrailingTextRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    '{"plan": ['
                    '{'
                    '"concept_id":"foundations",'
                    '"concept_name":"Elasticsearch Foundations",'
                    '"summary":"Understand indices, documents, mappings, and query basics.",'
                    '"prerequisites":[],'
                    '"resources":[{"title":"Elastic Intro","url":"https://example.com/intro","type":"doc"}],'
                    '"exercise":"Explain index, shard, and document flow in your own words.",'
                    '"confidence":0.45'
                    '},'
                    '{'
                    '"concept_id":"relevance",'
                    '"concept_name":"Search Relevance Tuning",'
                    '"summary":"Understand analyzers, BM25, boosts, and evaluation signals.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Relevance Guide","url":"https://example.com/relevance-guide","type":"doc"}],'
                    '"exercise":"Describe how you would debug weak ranking for a known query.",'
                    '"confidence":0.58'
                    '},'
                    '{'
                    '"concept_id":"vector_search",'
                    '"concept_name":"Vector Search Practice",'
                    '"summary":"Learn embeddings, kNN, and hybrid retrieval design.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"Hybrid Search Notes","url":"https://example.com/hybrid","type":"article"}],'
                    '"exercise":"Design a hybrid retrieval experiment for your use case.",'
                    '"confidence":0.62'
                    '},'
                    '{'
                    '"concept_id":"rag_systems",'
                    '"concept_name":"RAG Delivery Patterns",'
                    '"summary":"Combine storage, retrieval, prompting, and evaluation into a production flow.",'
                    '"prerequisites":["relevance","vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"exercise":"Outline a RAG architecture with retrieval, prompting, and feedback loops.",'
                    '"confidence":0.7'
                    '}'
                    ']}'
                    '\nRoadmap generated successfully.'
                )
            }
        return {"text": ""}


class AliasRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    '{"plan": ['
                    '{'
                    '"id":"foundations",'
                    '"title":"Elasticsearch Foundations",'
                    '"description":"Understand indices, documents, mappings, and query basics.",'
                    '"depends_on":[],'
                    '"resources":[{"name":"Elastic Intro","link":"https://example.com/intro","kind":"doc"}],'
                    '"task":"Explain index, shard, and document flow in your own words.",'
                    '"confidence":0.45'
                    '},'
                    '{'
                    '"id":"relevance",'
                    '"title":"Search Relevance Tuning",'
                    '"overview":"Understand analyzers, BM25, boosts, and evaluation signals.",'
                    '"depends_on":["foundations"],'
                    '"resources":[{"name":"Relevance Guide","link":"https://example.com/relevance-guide","kind":"doc"}],'
                    '"assignment":"Describe how you would debug weak ranking for a known query.",'
                    '"confidence":0.58'
                    '},'
                    '{'
                    '"id":"vector_search",'
                    '"topic":"Vector Search Practice",'
                    '"summary":"Learn embeddings, kNN, and hybrid retrieval design.",'
                    '"requirements":["foundations"],'
                    '"resources":[{"label":"Hybrid Search Notes","href":"https://example.com/hybrid","format":"article"}],'
                    '"project":"Design a hybrid retrieval experiment for your use case.",'
                    '"confidence":0.62'
                    '},'
                    '{'
                    '"id":"rag_systems",'
                    '"name":"RAG Delivery Patterns",'
                    '"objective":"Combine storage, retrieval, prompting, and evaluation into a production flow.",'
                    '"prerequisites":["relevance","vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"practical_exercise":"Outline a RAG architecture with retrieval, prompting, and feedback loops.",'
                    '"confidence":0.7'
                    '}'
                    ']}'
                )
            }
        return {"text": ""}


class PercentageConfidenceRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    '{"plan": ['
                    '{'
                    '"concept_id":"foundations",'
                    '"concept_name":"Python Programming Basics",'
                    '"summary":"Learn Python syntax, data structures, and control flow.",'
                    '"prerequisites":[],'
                    '"resources":[{"title":"Python Crash Course","url":"https://example.com/python","type":"book"}],'
                    '"exercise":"Write small Python scripts that process lists and dictionaries.",'
                    '"confidence":75'
                    '},'
                    '{'
                    '"concept_id":"ml_basics",'
                    '"concept_name":"Machine Learning Foundations",'
                    '"summary":"Understand supervised learning, preprocessing, and evaluation.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"ML Intro","url":"https://example.com/ml","type":"course"}],'
                    '"exercise":"Explain the difference between training, validation, and test sets.",'
                    '"confidence":"82%"'
                    '},'
                    '{'
                    '"concept_id":"vector_search",'
                    '"concept_name":"Embeddings and Vector Search",'
                    '"summary":"Learn embeddings, similarity search, and retrieval design.",'
                    '"prerequisites":["ml_basics"],'
                    '"resources":[{"title":"Vector Guide","url":"https://example.com/vector","type":"guide"}],'
                    '"exercise":"Describe how embeddings enable semantic retrieval.",'
                    '"confidence":0.68'
                    '},'
                    '{'
                    '"concept_id":"rag_systems",'
                    '"concept_name":"RAG Delivery Patterns",'
                    '"summary":"Combine retrieval, prompting, and evaluation in one workflow.",'
                    '"prerequisites":["vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"exercise":"Outline a RAG system for financial news understanding.",'
                    '"confidence":91'
                    '}'
                    ']}'
                )
            }
        return {"text": ""}


class TextConfidenceRoadmapLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '"What production search or RAG systems have you built so far?",'
                    '"How comfortable are you with Elasticsearch indexing and querying?",'
                    '"What do you know about embeddings, vector search, and hybrid retrieval?",'
                    '"Which backend languages and frameworks do you plan to use?",'
                    '"What delivery milestone do you want to hit in the next month?",'
                    '"What part of production AI systems feels least clear to you today?"'
                    ']}'
                )
            }
        if "Create a personalized technical learning roadmap as JSON." in prompt:
            return {
                "text": (
                    '{"plan": ['
                    '{'
                    '"concept_id":"foundations",'
                    '"concept_name":"Python Programming Basics",'
                    '"summary":"Learn Python syntax, data structures, and control flow.",'
                    '"prerequisites":[],'
                    '"resources":[{"title":"Python Crash Course","url":"https://example.com/python","type":"book"}],'
                    '"exercise":"Write small Python scripts that process lists and dictionaries.",'
                    '"confidence":"high"'
                    '},'
                    '{'
                    '"concept_id":"ml_basics",'
                    '"concept_name":"Machine Learning Foundations",'
                    '"summary":"Understand supervised learning, preprocessing, and evaluation.",'
                    '"prerequisites":["foundations"],'
                    '"resources":[{"title":"ML Intro","url":"https://example.com/ml","type":"course"}],'
                    '"exercise":"Explain the difference between training, validation, and test sets.",'
                    '"confidence":"medium"'
                    '},'
                    '{'
                    '"concept_id":"vector_search",'
                    '"concept_name":"Embeddings and Vector Search",'
                    '"summary":"Learn embeddings, similarity search, and retrieval design.",'
                    '"prerequisites":["ml_basics"],'
                    '"resources":[{"title":"Vector Guide","url":"https://example.com/vector","type":"guide"}],'
                    '"exercise":"Describe how embeddings enable semantic retrieval.",'
                    '"confidence":"7/10"'
                    '},'
                    '{'
                    '"concept_id":"rag_systems",'
                    '"concept_name":"RAG Delivery Patterns",'
                    '"summary":"Combine retrieval, prompting, and evaluation in one workflow.",'
                    '"prerequisites":["vector_search"],'
                    '"resources":[{"title":"RAG Patterns","url":"https://example.com/rag","type":"guide"}],'
                    '"exercise":"Outline a RAG system for financial news understanding.",'
                    '"confidence":"0,91"'
                    '}'
                    ']}'
                )
            }
        return {"text": ""}


class ObjectCalibrationLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    '{"questions": ['
                    '{"question":"Have you ever used a programming language before? If yes, which one?","assessment":"Prior knowledge"},'
                    '{"question":"What kind of software or automation projects have you completed before?","assessment":"Hands-on experience"},'
                    '{"question":"Have you built any API or backend application before?","assessment":"Hands-on experience"},'
                    '{"question":"What kind of AI engineer role are you aiming for specifically?","assessment":"Target outcome"},'
                    '{"question":"How comfortable are you with Linux, Docker, or command-line workflows?","assessment":"Tooling baseline"},'
                    '{"question":"What part of AI systems feels most unclear to you right now?","assessment":"Knowledge gap"}'
                    ']}'
                )
            }
        return {"text": ""}


class WrappedCalibrationLlmClient:
    async def generate(self, prompt, context=None, **kwargs):
        if "Create 6 calibration questions" in prompt:
            return {
                "text": (
                    "```json\n"
                    '{"questions": ['
                    '{"question":"Have you ever used a programming language before? If yes, which one?","assessment":"Prior knowledge"},'
                    '{"question":"What kind of software or automation projects have you completed before?","assessment":"Hands-on experience"},'
                    '{"question":"Have you built any API or backend application before?","assessment":"Hands-on experience"},'
                    '{"question":"What kind of AI engineer role are you aiming for specifically?","assessment":"Target outcome"},'
                    '{"question":"How comfortable are you with Linux, Docker, or command-line workflows?","assessment":"Tooling baseline"},'
                    '{"question":"What part of AI systems feels most unclear to you right now?","assessment":"Knowledge gap"}'
                    ']}\n'
                    "```\nQuestions ready."
                )
            }
        return {"text": ""}


class FakeElasticsearchClient:
    def __init__(self) -> None:
        self.interactions = []
        self.snapshots = []
        self.dependency_nodes = []
        self.learning_resources = []
        self.user_profiles = []

    async def store_interaction(self, *args, **kwargs):
        self.interactions.append((args, kwargs))
        return None

    async def store_snapshot(self, *args, **kwargs):
        self.snapshots.append((args, kwargs))
        return None

    async def store_dependency_node(self, *args, **kwargs):
        self.dependency_nodes.append((args, kwargs))
        return None

    async def store_learning_resource(self, *args, **kwargs):
        self.learning_resources.append((args, kwargs))
        return None

    async def upsert_user_profile(self, *args, **kwargs):
        self.user_profiles.append((args, kwargs))
        return None

    async def close(self):
        return None


class FakeSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionModel] = {}

    async def save(self, session_model: SessionModel) -> None:
        self._sessions[session_model.id] = session_model

    async def get(self, session_id: str) -> SessionModel | None:
        return self._sessions.get(session_id)

    async def list(self):  # pragma: no cover - not used in unit tests yet
        return list(self._sessions.values())


class FakeLabPrimerService:
    def generate(self, concept_name: str, goal: str, slug: str | None = None):
        return {
            "summary": f"Lab for {concept_name}",
            "docker-compose.yml": "services: {}",
            "Makefile": "up:\n\t@echo ok",
            "README.md": f"# {goal}",
            "notes.md": "notes",
        }


fake_session_manager_service = SessionManagerService()
fake_elastic = FakeElasticsearchClient()


def override_session_manager_service():
    return fake_session_manager_service


fake_session_repository = FakeSessionRepository()


def override_session_repository():
    return fake_session_repository


def setup_module(_module):
    global client
    app.dependency_overrides[get_embedding_client] = lambda: FakeEmbeddingClient()
    app.dependency_overrides[get_elasticsearch_client] = lambda: fake_elastic
    app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient()
    app.dependency_overrides[get_search_client] = lambda: FakeSearchClient()
    app.dependency_overrides[get_session_manager_service] = override_session_manager_service
    app.dependency_overrides[get_exercise_grader_service] = lambda: FakeGrader()
    app.dependency_overrides[get_session_repository] = override_session_repository
    app.dependency_overrides[get_lab_primer_service] = lambda: FakeLabPrimerService()
    client = TestClient(app)


def teardown_module(_module):
    global client
    app.dependency_overrides.clear()
    fake_session_manager_service._store.clear()
    fake_session_repository._sessions.clear()
    fake_elastic.interactions.clear()
    fake_elastic.snapshots.clear()
    fake_elastic.dependency_nodes.clear()
    fake_elastic.learning_resources.clear()
    fake_elastic.user_profiles.clear()
    client = None


client = None


def test_start_session_creates_session():
    response = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    assert response.status_code == 200
    session_response_document = response.json()
    assert session_response_document["goal"] == "Learn ESRE"
    assert session_response_document["messages"][-1]["metadata"]["stage"] == "calibration"
    assert session_response_document["messages"][-1]["content"] == "What production search or RAG systems have you built so far?"
    assert session_response_document.get("tuning_plan") == []


def test_start_session_accepts_object_calibration_questions():
    app.dependency_overrides[get_llm_client] = lambda: ObjectCalibrationLlmClient()

    try:
        response = client.post("/v1/sessions", json={"goal": "Become AI engineer"})
        assert response.status_code == 200
        session_response_document = response.json()
        assert (
            session_response_document["messages"][-1]["content"]
            == "Have you ever used a programming language before? If yes, which one?"
        )
    finally:
        app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient()
    assert len(fake_elastic.user_profiles) >= 1


def test_start_session_accepts_wrapped_calibration_questions():
    app.dependency_overrides[get_llm_client] = lambda: WrappedCalibrationLlmClient()

    try:
        response = client.post("/v1/sessions", json={"goal": "Become AI engineer"})
        assert response.status_code == 200
        session_response_document = response.json()
        assert (
            session_response_document["messages"][-1]["content"]
            == "Have you ever used a programming language before? If yes, which one?"
        )
    finally:
        app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient()


def test_start_session_returns_503_when_calibration_generation_fails():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: InvalidCalibrationLlmClient()
    try:
        response = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert response.status_code == 503
    assert "Calibration question generation" in response.json()["detail"]


def test_calibration_transitions_to_learning():
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]

    for i in range(6):
        response = client.post(
            f"/v1/sessions/{session_id}",
            json={"message": f"I am sharing calibration info iteration {i}"},
        )
        assert response.status_code == 200

    session_payload = client.get(f"/v1/sessions/{session_id}").json()
    assert session_payload["phase"] == "learning"
    assert len(session_payload.get("tuning_plan", [])) > 0
    assert session_payload["tuning_plan"][0]["concept_name"] == "Elasticsearch Foundations"
    assert session_payload["messages"][-1]["metadata"]["stage"] == "learning_intro"
    assert len(fake_elastic.dependency_nodes) >= 1
    assert len(fake_elastic.learning_resources) >= 1


def test_calibration_completion_returns_503_when_search_fails():
    original_search_override = app.dependency_overrides[get_search_client]
    app.dependency_overrides[get_search_client] = lambda: FailingSearchClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(5):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
            assert response.status_code == 200

        failure_response = client.post(
            f"/v1/sessions/{session_id}",
            json={"message": "I am sharing calibration info iteration 5"},
        )
    finally:
        app.dependency_overrides[get_search_client] = original_search_override

    assert failure_response.status_code == 503
    assert "Search agent failed" in failure_response.json()["detail"]


def test_calibration_completion_returns_503_when_roadmap_generation_fails():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: InvalidRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(5):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
            assert response.status_code == 200

        failure_response = client.post(
            f"/v1/sessions/{session_id}",
            json={"message": "I am sharing calibration info iteration 5"},
        )
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert failure_response.status_code == 503
    assert "Tuning roadmap generation" in failure_response.json()["detail"]


def test_calibration_completion_accepts_code_fenced_roadmap_json():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: WrappedRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
        final_response = response
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert final_response.status_code == 200
    final_response_document = final_response.json()
    assert final_response_document["session"]["phase"] == "learning"
    assert final_response_document["last_message"]["metadata"]["stage"] == "learning_intro"


def test_calibration_completion_accepts_roadmap_json_with_trailing_text():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: TrailingTextRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
        final_response = response
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert final_response.status_code == 200
    final_response_document = final_response.json()
    assert final_response_document["session"]["phase"] == "learning"
    assert final_response_document["last_message"]["metadata"]["stage"] == "learning_intro"


def test_calibration_completion_accepts_roadmap_alias_fields():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: AliasRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
        final_response = response
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert final_response.status_code == 200
    final_response_document = final_response.json()
    assert final_response_document["session"]["phase"] == "learning"
    assert final_response_document["session"]["tuning_plan"][0]["concept_name"] == "Elasticsearch Foundations"
    assert final_response_document["session"]["tuning_plan"][0]["exercise"] == "Explain index, shard, and document flow in your own words."


def test_calibration_completion_accepts_percentage_confidence_values():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: PercentageConfidenceRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
        final_response = response
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert final_response.status_code == 200
    final_response_document = final_response.json()
    tuning_plan = final_response_document["session"]["tuning_plan"]
    assert tuning_plan[0]["confidence"] == 0.75
    assert tuning_plan[1]["confidence"] == 0.82
    assert tuning_plan[3]["confidence"] == 0.91


def test_calibration_completion_accepts_textual_confidence_values():
    original_llm_override = app.dependency_overrides[get_llm_client]
    app.dependency_overrides[get_llm_client] = lambda: TextConfidenceRoadmapLlmClient()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"I am sharing calibration info iteration {i}"},
            )
        final_response = response
    finally:
        app.dependency_overrides[get_llm_client] = original_llm_override

    assert final_response.status_code == 200
    final_response_document = final_response.json()
    tuning_plan = final_response_document["session"]["tuning_plan"]
    assert tuning_plan[0]["confidence"] == 0.8
    assert tuning_plan[1]["confidence"] == 0.6
    assert tuning_plan[2]["confidence"] == 0.7
    assert tuning_plan[3]["confidence"] == 0.91


def test_learning_evaluation_advances_concept():
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]

    # Drive calibration to completion
    for i in range(6):
        client.post(
            f"/v1/sessions/{session_id}",
            json={"message": f"Calibration answer iteration {i}"},
        )

    # Submit learning answer with enough detail to pass placeholder evaluation
    learning_answer = (
        "I reviewed the docs about indices, shards, and relevance scoring. "
        "My plan is to run experiments comparing vector and keyword retrieval while documenting the setup."
    )
    response = client.post(
        f"/v1/sessions/{session_id}",
        json={"message": learning_answer},
    )
    assert response.status_code == 200
    session_message_response_document = response.json()
    assert session_message_response_document["session"]["phase"] in {"learning", "learning_complete"}
    # assistant encourages next steps or completion
    assert session_message_response_document["last_message"]["metadata"]["stage"] in {
        "learning_next",
        "learning_complete",
    }


def test_learning_answer_returns_503_when_grading_fails():
    original_grader_override = app.dependency_overrides[get_exercise_grader_service]
    app.dependency_overrides[get_exercise_grader_service] = lambda: FailingGrader()
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]
    try:
        for i in range(6):
            calibration_response = client.post(
                f"/v1/sessions/{session_id}",
                json={"message": f"Calibration answer iteration {i}"},
            )
            assert calibration_response.status_code == 200

        response = client.post(
            f"/v1/sessions/{session_id}",
            json={"message": "I reviewed the docs and prepared an answer."},
        )
    finally:
        app.dependency_overrides[get_exercise_grader_service] = original_grader_override

    assert response.status_code == 503
    assert "Exercise grading failed" in response.json()["detail"]


def test_lab_primer_returns_recipe():
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]

    response = client.post(
        f"/v1/sessions/{session_id}",
        json={"message": "/lab foundations"},
    )
    assert response.status_code == 200
    session_message_response_document = response.json()
    assert session_message_response_document["last_message"]["metadata"]["stage"] == "lab_primer"
    assert "docker-compose.yml" in session_message_response_document["last_message"]["content"]
