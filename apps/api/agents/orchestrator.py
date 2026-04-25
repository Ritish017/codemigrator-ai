"""
LangGraph orchestrator wiring the 5 agents together.

State flows: Reader -> Architect -> Migrator -> Tester -> Documenter.
After Architect, if complexity == "simple" we still run Tester (the demo wins
on showing all 5 agents firing). The router exists for future use.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from langgraph.graph import END, StateGraph
from loguru import logger

from agents import architect, documenter, migrator, reader, tester
from llm.nemotron import NemotronClient, get_client
from models.outputs import MigrationReport
from models.state import MigrationState, SourceFile


# ---------- Node implementations ----------

async def reader_node(state: MigrationState) -> MigrationState:
    client = get_client()
    state["current_step"] = "reader"
    state["progress_percent"] = 5.0
    analysis = await reader.run(client, state["source_files"])
    state["analysis"] = analysis
    state["progress_percent"] = 20.0
    state["metrics"] = client.get_metrics()
    return state


async def architect_node(state: MigrationState) -> MigrationState:
    client = get_client()
    state["current_step"] = "architect"
    state["progress_percent"] = 25.0
    plan = await architect.run(
        client,
        state["source_files"],
        state["analysis"],
        state.get("target_language", "python"),
    )
    state["plan"] = plan
    state["progress_percent"] = 45.0
    state["metrics"] = client.get_metrics()
    return state


async def migrator_node(state: MigrationState) -> MigrationState:
    client = get_client()
    state["current_step"] = "migrator"
    state["progress_percent"] = 50.0
    results = await migrator.run(client, state["plan"], state["source_files"])
    state["migrations"] = results
    state["progress_percent"] = 75.0
    state["metrics"] = client.get_metrics()
    return state


async def tester_node(state: MigrationState) -> MigrationState:
    client = get_client()
    state["current_step"] = "tester"
    state["progress_percent"] = 80.0
    suite = await tester.run(client, state["plan"], state["migrations"])
    state["tests"] = suite
    state["progress_percent"] = 90.0
    state["metrics"] = client.get_metrics()
    return state


async def documenter_node(state: MigrationState) -> MigrationState:
    client = get_client()
    state["current_step"] = "documenter"
    state["progress_percent"] = 92.0
    metrics = client.get_metrics()
    report = await documenter.run(
        client,
        state["analysis"],
        state["plan"],
        state["migrations"],
        state.get("tests"),
        metrics,
    )
    state["report"] = report
    state["progress_percent"] = 100.0
    state["current_step"] = "complete"
    state["metrics"] = client.get_metrics()
    return state


# ---------- Graph wiring ----------

def build_graph():
    g = StateGraph(MigrationState)
    g.add_node("reader", reader_node)
    g.add_node("architect", architect_node)
    g.add_node("migrator", migrator_node)
    g.add_node("tester", tester_node)
    g.add_node("documenter", documenter_node)

    g.set_entry_point("reader")
    g.add_edge("reader", "architect")
    g.add_edge("architect", "migrator")
    g.add_edge("migrator", "tester")
    g.add_edge("tester", "documenter")
    g.add_edge("documenter", END)
    return g.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ---------- High-level helpers ----------

async def run_migration(
    source_files: list[SourceFile], target_language: str = "python"
) -> MigrationState:
    """Run the full pipeline and return the final state."""
    initial: MigrationState = {
        "source_files": source_files,
        "target_language": target_language,
        "source_language": source_files[0]["language"] if source_files else "cobol",
        "current_step": "init",
        "progress_percent": 0.0,
        "metrics": {},
        "errors": [],
        "events": [],
        "migrations": [],
    }
    graph = get_graph()
    final_state = await graph.ainvoke(initial)
    return final_state


async def stream_migration(
    source_files: list[SourceFile], target_language: str = "python"
) -> AsyncIterator[dict]:
    """Async iterator yielding state updates for SSE.

    LangGraph's astream emits state after each node — perfect for our timeline UI.
    """
    initial: MigrationState = {
        "source_files": source_files,
        "target_language": target_language,
        "source_language": source_files[0]["language"] if source_files else "cobol",
        "current_step": "init",
        "progress_percent": 0.0,
        "metrics": {},
        "errors": [],
        "events": [],
        "migrations": [],
    }
    graph = get_graph()
    try:
        async for chunk in graph.astream(initial):
            # chunk is {node_name: state_diff}
            for node_name, state_diff in chunk.items():
                yield {"node": node_name, "state": state_diff}
    except Exception as exc:
        logger.exception("orchestrator: pipeline failed")
        yield {"node": "error", "state": {"errors": [str(exc)]}}
