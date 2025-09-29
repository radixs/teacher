from __future__ import annotations

from fastapi import FastAPI

from .routes import search

app = FastAPI(title="Search Agent", version="0.1.0")
app.include_router(search.router, prefix="/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
