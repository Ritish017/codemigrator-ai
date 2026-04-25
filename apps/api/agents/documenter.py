"""
DOCUMENTER agent — runs on Nemotron 3 Nano.

Synthesizes everything into a polished markdown migration report.
"""
from __future__ import annotations

from loguru import logger

from llm.nemotron import NemotronClient
from llm.prompts import DOCUMENTER_SYSTEM
from models.outputs import (
    CodebaseAnalysis,
    MigrationPlan,
    MigrationReport,
    MigrationResult,
    TestSuite,
)


async def run(
    client: NemotronClient,
    analysis: CodebaseAnalysis,
    plan: MigrationPlan,
    migrations: list[MigrationResult],
    tests: TestSuite | None,
    metrics: dict,
) -> MigrationReport:
    logger.info("documenter.start")

    files_table = "\n".join(
        f"| {m.source_file} | {m.target_file} | {m.confidence:.2f} | {len(m.warnings)} |"
        for m in migrations
    )
    test_summary = (
        f"{len(tests.test_files)} test files, ~{tests.coverage_estimate:.0%} coverage" if tests else "no tests generated"
    )

    prompt = f"""Synthesize the full migration report.

CODEBASE ANALYSIS:
{analysis.model_dump_json(indent=2)}

MIGRATION PLAN:
{plan.model_dump_json(indent=2)}

FILE MIGRATIONS (table-ready):
| Source | Target | Confidence | Warnings |
|--------|--------|------------|----------|
{files_table}

TESTS: {test_summary}

NEMOTRON METRICS:
{metrics}

Produce a Markdown report with sections:
1. Executive Summary
2. Source Codebase Overview
3. Target Architecture & Rationale
4. File-by-File Migration Table
5. Modernization Changes
6. Risks & Follow-up Work
7. Test Strategy & Coverage
8. Nemotron Usage (Super vs Nano routing, tokens, cost)

Keep it professional, concrete, and skim-friendly.
"""

    report = await client.call(
        prompt=prompt,
        tier="nano",
        system=DOCUMENTER_SYSTEM,
        response_model=MigrationReport,
        max_tokens=6000,
        temperature=0.4,
    )
    logger.success("documenter.done bytes={}", len(report.markdown))
    return report
