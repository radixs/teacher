from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_start_session_creates_session():
    response = client.post("/v1/sessions", json={"goal": "Learn ESRE"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["goal"] == "Learn ESRE"
    assert payload["messages"], "Session should include system + assistant messages"
