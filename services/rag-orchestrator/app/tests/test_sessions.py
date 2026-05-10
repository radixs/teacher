from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import (
    get_elasticsearch_client,
    get_embedding_client,
    get_llm_client,
    get_search_client,
    get_session_manager,
    get_exercise_grader,
    get_session_store,
)
from app.services.session_manager import SessionManager
from app.models.session import Session


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
                    '"How much time can you spend each week on practice and labs?"'
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


class FakeGrader:
    async def evaluate(self, concept, answer):
        return {
            "passed": True,
            "score": 0.9,
            "feedback": "Looks good.",
            "highlights": [concept.get("concept_name")],
        }


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


class FakeSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def save(self, session: Session) -> None:
        self._sessions[session.id] = session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def list(self):  # pragma: no cover - not used in unit tests yet
        return list(self._sessions.values())


fake_session_manager = SessionManager()
fake_elastic = FakeElasticsearchClient()


def override_session_manager():
    return fake_session_manager


fake_session_store = FakeSessionStore()


def override_session_store():
    return fake_session_store


def setup_module(_module):
    global client
    app.dependency_overrides[get_embedding_client] = lambda: FakeEmbeddingClient()
    app.dependency_overrides[get_elasticsearch_client] = lambda: fake_elastic
    app.dependency_overrides[get_llm_client] = lambda: FakeLlmClient()
    app.dependency_overrides[get_search_client] = lambda: FakeSearchClient()
    app.dependency_overrides[get_session_manager] = override_session_manager
    app.dependency_overrides[get_exercise_grader] = lambda: FakeGrader()
    app.dependency_overrides[get_session_store] = override_session_store
    client = TestClient(app)


def teardown_module(_module):
    global client
    app.dependency_overrides.clear()
    fake_session_manager._store.clear()
    fake_session_store._sessions.clear()
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
    payload = response.json()
    assert payload["goal"] == "Learn ESRE"
    assert payload["messages"][-1]["metadata"]["stage"] == "calibration"
    assert payload["messages"][-1]["content"] == "What production search or RAG systems have you built so far?"
    assert payload.get("tuning_plan") == []
    assert len(fake_elastic.user_profiles) >= 1


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
    data = response.json()
    assert data["session"]["phase"] in {"learning", "learning_complete"}
    # assistant encourages next steps or completion
    assert data["last_message"]["metadata"]["stage"] in {"learning_next", "learning_complete"}

def test_lab_primer_returns_recipe():
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]

    response = client.post(
        f"/v1/sessions/{session_id}",
        json={"message": "/lab foundations"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["last_message"]["metadata"]["stage"] == "lab_primer"
    assert "docker-compose.yml" in data["last_message"]["content"]
