"""
TESTER agent — two-phase: Super designs strategy, Nano writes test cases.
"""
from __future__ import annotations

from loguru import logger
from pydantic import BaseModel, Field

from llm.nemotron import NemotronClient
from llm.prompts import TESTER_CASES_SYSTEM, TESTER_STRATEGY_SYSTEM
from models.outputs import MigrationPlan, MigrationResult, TestSuite
from utils.codecheck import run_tests, missing_local_imports, module_name, sanitize_python, syntax_error, undefined_names


class TestStrategy(BaseModel):
    strategy: str = Field(..., description="High-level test strategy")
    priorities: list[str] = Field(default_factory=list)
    coverage_target: float = Field(..., ge=0.0, le=1.0)


async def run(
    client: NemotronClient,
    plan: MigrationPlan,
    migrations: list[MigrationResult],
) -> TestSuite:
    logger.info("tester.start migrations={}", len(migrations))

    # Phase 1: Super designs the strategy (deep reasoning).
    plan_summary = (
        f"Target: {plan.target_architecture.framework}\n"
        f"Files migrated: {len(migrations)}\n"
        f"Patterns: {', '.join(plan.target_architecture.key_patterns)}\n"
    )
    code_index = "\n".join(
        f"- {m.target_file} (confidence={m.confidence:.2f}, warnings={len(m.warnings)})"
        for m in migrations
    )

    strategy_prompt = f"""Migration context:
{plan_summary}

Files migrated:
{code_index}

Architect's risk assessment:
{chr(10).join("- " + r for r in plan.risk_assessment)}

Design a test strategy that catches the highest-impact regressions first.
"""
    strategy = await client.call(
        prompt=strategy_prompt,
        tier="super",
        system=TESTER_STRATEGY_SYSTEM,
        response_model=TestStrategy,
        max_tokens=2048,
        temperature=0.4,
    )
    logger.info("tester.strategy coverage_target={}", strategy.coverage_target)

    # Phase 2: Nano generates test files.
    code_block = "\n\n".join(
        f"=== {m.target_file} ===\n{m.migrated_code}" for m in migrations
    )
    cases_prompt = f"""Test strategy (from Super phase):
{strategy.model_dump_json(indent=2)}

Migrated code to test:
{code_block}

Migrated modules and their import paths (import ONLY these project modules):
{chr(10).join(f"- {m.target_file} -> import as `{module_name(m.target_file)}`" for m in migrations)}

Generate executable pytest test files. Each file must be valid Python that runs as-is.
"""
    known = {module_name(m.target_file) for m in migrations}
    feedback = ""
    best: tuple[TestSuite, int] | None = None
    for attempt in range(3):
        suite = await client.call(
            prompt=cases_prompt + feedback,
            tier="nano",
            system=TESTER_CASES_SYSTEM,
            response_model=TestSuite,
            max_tokens=16000,
            temperature=0.3,
        )
        problems = []
        for tf in suite.test_files:
            tf.code = sanitize_python(tf.code)
            if err := syntax_error(tf.code):
                problems.append(f"{tf.filename}: SyntaxError at {err}")
            if missing := missing_local_imports(tf.code, known):
                problems.append(f"{tf.filename}: imports non-existent modules {', '.join(missing)}")
            if undef := undefined_names(tf.code):
                problems.append(f"{tf.filename}: uses names never defined or imported: {', '.join(undef)} (import them from the migrated module that defines them)")
        if not problems:
            # Static checks pass: actually run the suite. Only collection errors
            # (imports, undefined names) are fed back, never assertion failures.
            run = run_tests(
                {m.target_file: m.migrated_code for m in migrations},
                {tf.filename.split("/")[-1]: tf.code for tf in suite.test_files},
            )
            suite.notes = (suite.notes + f"\nExecution check: {run['summary']}").strip()
            logger.info("tester: execution check attempt {}: {}", attempt + 1, run["summary"])
            if run["collection_errors"]:
                problems = [f"test collection error: {e}" for e in run["collection_errors"]]
            if best is None or run["passed"] > best[1]:
                best = (suite, run["passed"])
        if not problems:
            break
        logger.warning("tester: attempt {} invalid: {}", attempt + 1, problems)
        feedback = (
            "\n\nYour previous test files were rejected: " + "; ".join(problems)
            + ". Fix these and return all test files again."
        )

    if best is not None:
        suite = best[0]

    # Stitch in the strategy text from Super into the suite.
    suite.strategy = strategy.strategy
    logger.success("tester.done test_files={} coverage={}", len(suite.test_files), suite.coverage_estimate)
    return suite
