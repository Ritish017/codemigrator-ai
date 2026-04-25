"""SSE event helpers for streaming agent progress to the frontend."""
from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, **payload: Any) -> dict[str, str]:
    """Format a payload for sse-starlette's EventSourceResponse."""
    return {"event": event_type, "data": json.dumps({"type": event_type, **payload})}


def progress(step: str, percent: float, message: str = "") -> dict[str, str]:
    return sse_event("progress", step=step, percent=round(percent, 1), message=message)


def agent_thinking(agent: str, delta: str) -> dict[str, str]:
    return sse_event("agent_thinking", agent=agent, delta=delta)


def agent_complete(agent: str, summary: str = "", data: dict | None = None) -> dict[str, str]:
    return sse_event("agent_complete", agent=agent, summary=summary, data=data or {})


def metrics_update(metrics: dict) -> dict[str, str]:
    return sse_event("metrics", metrics=metrics)


def error_event(message: str, agent: str | None = None) -> dict[str, str]:
    return sse_event("error", message=message, agent=agent)


def complete_event(result: dict) -> dict[str, str]:
    return sse_event("complete", result=result)
