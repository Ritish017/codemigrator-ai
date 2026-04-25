"""Health check route."""
from __future__ import annotations

from fastapi import APIRouter

from llm.nemotron import MODEL_MAP, get_client

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Light health check — does not call Nemotron."""
    try:
        client = get_client()
        configured = bool(client.api_key)
    except Exception as exc:
        return {"status": "degraded", "nemotron": "unconfigured", "error": str(exc)}
    return {
        "status": "ok",
        "nemotron": "configured" if configured else "unconfigured",
        "models": MODEL_MAP,
    }


@router.get("/health/ping")
async def ping_nemotron() -> dict:
    """Active probe — actually calls Nano with a tiny prompt."""
    client = get_client()
    try:
        text = await client.call(
            prompt="Reply with only the word 'pong'.",
            tier="nano",
            max_tokens=8,
            temperature=0.0,
        )
        return {"status": "ok", "reply": text.strip()[:32]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
