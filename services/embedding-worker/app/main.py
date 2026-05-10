from __future__ import annotations

from functools import lru_cache
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field
import torch

from .flow_logger import log_flow

if hasattr(torch.utils, '_pytree') and not hasattr(torch.utils._pytree, 'register_pytree_node'):
    _legacy_register = torch.utils._pytree._register_pytree_node  # type: ignore[attr-defined]

    def _compat_register_pytree_node(*args, **kwargs):
        allowed = {k: v for k, v in kwargs.items() if k in {'namespace', 'name', 'priority'}}
        return _legacy_register(*args, **allowed)

    torch.utils._pytree.register_pytree_node = _compat_register_pytree_node  # type: ignore[attr-defined]

from sentence_transformers import SentenceTransformer


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    embedding: List[float]
    model: str


app = FastAPI(title="Embedding Worker", version="0.1.0")


def resolve_model_id(model: SentenceTransformer, configured_name: str) -> str:
    model_card_data = getattr(model, "model_card_data", None)
    if isinstance(model_card_data, dict) and model_card_data.get("model_id"):
        return str(model_card_data["model_id"])

    card_model_id = getattr(model_card_data, "model_id", None)
    if card_model_id:
        return str(card_model_id)

    model_name_or_path = getattr(model, "model_name_or_path", None)
    if model_name_or_path:
        return str(model_name_or_path)

    return configured_name


@lru_cache()
def get_model() -> SentenceTransformer:
    import os

    model_name = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
    device = os.environ.get("EMBEDDING_DEVICE", "cpu")
    model = SentenceTransformer(model_name, device=device)
    resolved_model_id = resolve_model_id(model, model_name)
    log_flow(
        "embedding-worker",
        "model.loaded",
        "Embedding worker loaded the sentence-transformer model into memory.",
        model=resolved_model_id,
        device=device,
    )
    return model


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest) -> EmbedResponse:
    import os

    log_flow(
        "embedding-worker",
        "embed.received",
        "Embedding worker received text to convert into a vector.",
        text=request.text,
        text_length=len(request.text),
    )
    model = get_model()
    vector = model.encode(request.text, normalize_embeddings=True)
    configured_model_name = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
    response = EmbedResponse(
        embedding=vector.tolist(),
        model=resolve_model_id(model, configured_model_name),
    )
    log_flow(
        "embedding-worker",
        "embed.completed",
        "Embedding worker returned a normalized embedding vector.",
        dimensions=len(response.embedding),
        model=response.model,
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    import os

    model = get_model()
    configured_model_name = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
    resolved_model_id = resolve_model_id(model, configured_model_name)
    log_flow(
        "embedding-worker",
        "health.checked",
        "Embedding worker health endpoint was called.",
        model=resolved_model_id,
    )
    return {"status": "ok", "model": resolved_model_id}
