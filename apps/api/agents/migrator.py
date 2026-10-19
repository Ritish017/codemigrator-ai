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
from utils.codecheck import import_errors, missing_local_imports, module_name, sanitize_python, syntax_error, undefined_names


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

Target modules in this migration (the ONLY project modules you may import):
{chr(10).join("- " + module_name(f.target_file) for f in plan.file_migration_order)}

Produce the migrated code for {file_spec.target_file}. Follow the architecture exactly.
"""

    known = {module_name(f.target_file) for f in plan.file_migration_order}
    feedback = ""
    result: MigrationResult | None = None
    for attempt in range(2):
        result = await client.call(
            prompt=prompt + feedback,
            tier="nano",
            system=MIGRATOR_SYSTEM,
            response_model=MigrationResult,
            max_tokens=6000,
            temperature=0.3,
        )
        result.migrated_code = sanitize_python(result.migrated_code)
        problems = []
        if err := syntax_error(result.migrated_code):
            problems.append(f"SyntaxError at {err}")
        if missing := missing_local_imports(result.migrated_code, known):
            problems.append("imports modules that are not generated: " + ", ".join(missing))
        if undef := undefined_names(result.migrated_code):
            problems.append("uses names that are never defined or imported: " + ", ".join(undef))
        if not problems:
            return result
        logger.warning("migrator: {} attempt {} invalid: {}", file_spec.target_file, attempt + 1, problems)
        feedback = (
            "\n\nYour previous output was rejected: " + "; ".join(problems)
            + ". Fix this and return the full corrected file."
        )
    assert result is not None
    result.warnings.append("Automatic validation still failed after retry: " + feedback.strip())
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

    # Import every generated module together; re-migrate any file that fails to import.
    broken = import_errors({r.target_file: r.migrated_code for r in results})
    if broken:
        logger.warning("migrator: import check failed: {}", broken)
        specs = {f.target_file: f for f in plan.file_migration_order}
        for i, r in enumerate(results):
            if r.target_file not in broken or r.target_file not in specs:
                continue
            spec = specs[r.target_file]
            source = _find_source(source_files, spec.source_file)
            if source is None:
                continue
            others = [o for o in results if o.target_file != r.target_file]
            fixed_spec = spec.model_copy(update={
                "migration_notes": spec.migration_notes
                + f"\n\nA previous version failed to import with: {broken[r.target_file]}. "
                "Import names only from the modules that actually define them (see reference files)."
            })
            try:
                results[i] = await _migrate_one(client, fixed_spec, source, plan, others)
            except Exception as exc:  # noqa: BLE001
                logger.error("migrator: retry failed for {}: {}", r.target_file, exc)
        still = import_errors({r.target_file: r.migrated_code for r in results})
        for r in results:
            if r.target_file in still:
                r.warnings.append(f"Module does not import cleanly: {still[r.target_file]}")

    logger.success("migrator.done success={}/{}", len(results), len(plan.file_migration_order))
    return results
