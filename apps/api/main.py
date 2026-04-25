"""
FastAPI entrypoint for CodeMigrator AI.

100% Python backend. 100% NVIDIA Nemotron 3.
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from routes import health, migrate

# Configure loguru once at import.
logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
)

app = FastAPI(
    title="CodeMigrator AI",
    description="Multi-agent legacy code migration · Powered by NVIDIA Nemotron 3 (Super + Nano)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(migrate.router, prefix="/api", tags=["migrate"])


@app.get("/")
async def root() -> dict:
    return {
        "name": "CodeMigrator AI",
        "powered_by": "NVIDIA Nemotron 3 Super + Nano",
        "tier_routing": {
            "super": "nvidia/nemotron-3-super-120b-a12b",
            "nano": "nvidia/nemotron-3-nano-30b-a3b",
        },
        "endpoints": [
            "GET  /api/health",
            "GET  /api/health/ping",
            "GET  /api/sample",
            "POST /api/migrate",
            "POST /api/migrate/sample",
        ],
    }
