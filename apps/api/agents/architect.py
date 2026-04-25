"""
ARCHITECT agent — runs on Nemotron 3 Super (120B).

This is the showcase agent. It receives the FULL codebase plus the Reader's
analysis and designs the entire migration plan in a single Super call.
The 1M-token context window is what makes this possible without chunking.
"""
from __future__ import annotations

from loguru import logger

from llm.nemotron import NemotronClient
from llm.prompts import ARCHITECT_SYSTEM
from models.outputs import CodebaseAnalysis, MigrationPlan
from models.state import SourceFile


async def run(
    client: NemotronClient,
    source_files: list[SourceFile],
    analysis: CodebaseAnalysis,
    target_language: str,
) -> MigrationPlan:
    logger.info(
        "architect.start target={} modules={} complexity={}",
        target_language,
        len(analysis.modules),
        analysis.estimated_complexity,
    )

    # Hand Super the entire codebase. Showcase the 1M context.
    full_source_block = "\n\n".join(
        f"=== {sf['path']} ===\n{sf['content']}" for sf in source_files
    )

    prompt = f"""Target language: {target_language}

CODEBASE ANALYSIS (from the Reader agent):
{analysis.model_dump_json(indent=2)}

FULL SOURCE CODE (entire codebase, no truncation):
{full_source_block}

Now design the complete migration plan. Be opinionated and specific:
- Choose a concrete framework, not a category.
- Map every source file to a target file.
- Order migrations such that dependencies are migrated first.
- Identify the top 3-5 modernization opportunities by name.
- Call out risks honestly.
- In `architectural_rationale`, write 2-3 paragraphs justifying your design.
  This is where your reasoning shines — show your work.
"""

    plan = await client.call(
        prompt=prompt,
        tier="super",
        system=ARCHITECT_SYSTEM,
        response_model=MigrationPlan,
        max_tokens=8192,
        temperature=0.5,
    )
    logger.success(
        "architect.done framework={} files={} effort_h={}",
        plan.target_architecture.framework,
        len(plan.file_migration_order),
        plan.estimated_effort_hours,
    )
    return plan
