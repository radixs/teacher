from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import (
    get_elasticsearch_client,
    get_embedding_client,
    get_session_manager,
    get_exercise_grader,
)
from app.services.session_manager import SessionManager


class FakeEmbeddingClient:
    async def embed(self, text: str):
        return [0.0, 0.1, 0.2]


class FakeGrader:
    async def evaluate(self, concept, answer):
        return {
            "passed": True,
            "score": 0.9,
            "feedback": "Looks good.",
            "highlights": [concept.get("concept_name")],
        }


class FakeElasticsearchClient:
    async def store_interaction(self, *args, **kwargs):
        return None

    async def store_snapshot(self, *args, **kwargs):
        return None

    async def store_dependency_node(self, *args, **kwargs):
        return None

    async def close(self):
        return None


def override_session_manager():
    return SessionManager()


def setup_module(_module):
    app.dependency_overrides[get_embedding_client] = lambda: FakeEmbeddingClient()
    app.dependency_overrides[get_elasticsearch_client] = lambda: FakeElasticsearchClient()
    app.dependency_overrides[get_session_manager] = override_session_manager
    app.dependency_overrides[get_exercise_grader] = lambda: FakeGrader()


def teardown_module(_module):
    app.dependency_overrides.clear()


client = TestClient(app)


def test_start_session_creates_session():
    response = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["goal"] == "Learn ESRE"
    assert payload["messages"][-1]["metadata"]["stage"] == "calibration"
    assert payload.get("tuning_plan") == []


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
    assert session_payload["messages"][-1]["metadata"]["stage"] == "learning_intro"


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
