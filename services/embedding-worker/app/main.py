from __future__ import annotations

from functools import lru_cache
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    embedding: List[float]
    model: str


app = FastAPI(title="Embedding Worker", version="0.1.0")


@lru_cache()
def get_model() -> SentenceTransformer:
    import os

    model_name = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
    device = os.environ.get("EMBEDDING_DEVICE", "cpu")
    return SentenceTransformer(model_name, device=device)


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest) -> EmbedResponse:
    model = get_model()
    vector = model.encode(request.text, normalize_embeddings=True)
    return EmbedResponse(embedding=vector.tolist(), model=model.model_card_data.get("model_id", "unknown"))


@app.get("/health")
async def health() -> dict[str, str]:
    model = get_model()
    return {"status": "ok", "model": model.model_card_data.get("model_id", "unknown")}
