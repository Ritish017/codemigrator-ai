"""LangGraph state shared across the agent workflow."""
from __future__ import annotations

from typing import Any, TypedDict

from models.outputs import (
    CodebaseAnalysis,
    MigrationPlan,
    MigrationReport,
    MigrationResult,
    TestSuite,
)


class SourceFile(TypedDict):
    path: str
    content: str
    language: str


class MigrationState(TypedDict, total=False):
    # Inputs
    source_files: list[SourceFile]
    target_language: str
    source_language: str

    # Agent outputs
    analysis: CodebaseAnalysis | None
    plan: MigrationPlan | None
    migrations: list[MigrationResult]
    tests: TestSuite | None
    report: MigrationReport | None

    # Streaming bookkeeping
    current_step: str
    progress_percent: float
    metrics: dict[str, Any]
    errors: list[str]
    events: list[dict[str, Any]]
