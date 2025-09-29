from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import (
    get_elasticsearch_client,
    get_embedding_client,
    get_session_manager,
)
from app.services.session_manager import SessionManager


class FakeEmbeddingClient:
    async def embed(self, text: str):
        return [0.0, 0.1, 0.2]


class FakeElasticsearchClient:
    async def store_interaction(self, *args, **kwargs):  # noqa: D401
        return None

    async def store_snapshot(self, *args, **kwargs):
        return None

    async def close(self):
        return None


def override_session_manager():
    return SessionManager()


def setup_module(_module):
    app.dependency_overrides[get_embedding_client] = lambda: FakeEmbeddingClient()
    app.dependency_overrides[get_elasticsearch_client] = lambda: FakeElasticsearchClient()
    app.dependency_overrides[get_session_manager] = override_session_manager


def teardown_module(_module):
    app.dependency_overrides.clear()


client = TestClient(app)


def test_start_session_creates_session():
    response = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["goal"] == "Learn ESRE"
    assert payload["messages"][-1]["role"] == "assistant"
    assert payload["messages"][-1]["metadata"]["stage"] == "calibration"


def test_calibration_progression_moves_to_tuning():
    start = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    session_id = start.json()["id"]

    # answer enough questions to exhaust calibration queue
    for i in range(6):
        response = client.post(
            f"/v1/sessions/{session_id}",
            json={"message": f"answer {i}"},
        )
        assert response.status_code == 200

    data = client.get(f"/v1/sessions/{session_id}").json()
    assert data["phase"] in {"calibration", "tuning"}
