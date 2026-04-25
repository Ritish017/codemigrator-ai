"""
MIGRATOR agent — runs on Nemotron 3 Nano in parallel.

For each file in the migration plan, we kick off a Nano call. The semaphore
inside NemotronClient throttles to 15 concurrent (40 req/min free tier).
"""
from __future__ import annotations

import asyncio

from loguru import logger

from llm.nemotron import NemotronClient
from llm.prompts import MIGRATOR_SYSTEM
from models.outputs import FileToMigrate, MigrationPlan, MigrationResult
from models.state import SourceFile


def _find_source(files: list[SourceFile], path: str) -> SourceFile | None:
    for sf in files:
        if sf["path"] == path:
            return sf
    return None


async def _migrate_one(
    client: NemotronClient,
    file_spec: FileToMigrate,
    source: SourceFile,
    plan: MigrationPlan,
    already_done: list[MigrationResult],
) -> MigrationResult:
    context_block = ""
    if already_done:
        # Show up to 3 most-recent migrations as style/consistency reference.
        recent = already_done[-3:]
        context_block = "\n\n".join(
            f"--- Already migrated: {m.target_file} ---\n{m.migrated_code[:1500]}"
            for m in recent
        )

    prompt = f"""Architectural plan summary:
- Target framework: {plan.target_architecture.framework}
- Key patterns: {", ".join(plan.target_architecture.key_patterns)}
- Data layer: {plan.target_architecture.data_layer}

Source file to migrate: {file_spec.source_file}
Target file path: {file_spec.target_file}

Architect's notes for this specific file:
{file_spec.migration_notes}

Source code:
```
{source["content"]}
```

{f'Reference (already-migrated files for consistency):\\n{context_block}' if context_block else ''}

Produce the migrated code for {file_spec.target_file}. Follow the architecture exactly.
"""

    result = await client.call(
        prompt=prompt,
        tier="nano",
        system=MIGRATOR_SYSTEM,
        response_model=MigrationResult,
        max_tokens=6000,
        temperature=0.3,
    )
    return result


async def run(
    client: NemotronClient,
    plan: MigrationPlan,
    source_files: list[SourceFile],
) -> list[MigrationResult]:
    logger.info("migrator.start files={}", len(plan.file_migration_order))

    # Sort by priority so dependencies-first ordering is preserved when
    # running sequentially within priority bands. We still parallelize within
    # the same priority level for speed.
    by_priority: dict[int, list[FileToMigrate]] = {}
    for spec in plan.file_migration_order:
        by_priority.setdefault(spec.priority, []).append(spec)

    results: list[MigrationResult] = []
    for priority in sorted(by_priority.keys()):
        batch = by_priority[priority]
        logger.info("migrator.batch priority={} files={}", priority, len(batch))

        coros = []
        for spec in batch:
            source = _find_source(source_files, spec.source_file)
            if source is None:
                logger.warning("migrator: source file not found, skipping: {}", spec.source_file)
                continue
            coros.append(_migrate_one(client, spec, source, plan, results))

        batch_results = await asyncio.gather(*coros, return_exceptions=True)
        for r in batch_results:
            if isinstance(r, Exception):
                logger.error("migrator: file failed: {}", r)
                continue
            results.append(r)

    logger.success("migrator.done success={}/{}", len(results), len(plan.file_migration_order))
    return results
