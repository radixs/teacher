from fastapi.testclient import TestClient

from app.main import app


def test_embed_returns_vector(monkeypatch):
    class FakeModel:
        def __init__(self, *args, **kwargs):
            self.model_card_data = {"model_id": "fake"}

        def encode(self, text, normalize_embeddings=True):
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr("app.main.get_model", lambda: FakeModel())

    client = TestClient(app)
    response = client.post("/embed", json={"text": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["embedding"] == [0.1, 0.2, 0.3]
    assert data["model"] == "fake"
