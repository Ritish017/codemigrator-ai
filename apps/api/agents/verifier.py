"""
VERIFIER agent — golden-file equivalence against the original COBOL.

Nano writes a small adapter that feeds a fixed scenario through the migrated modules.
Fixed code then compares the adapter's results with outputs recorded from the legacy
programs under GnuCOBOL (tools/golden/). Only crashes are fed back for a retry, never
mismatches, so the model cannot tune the adapter toward the expected numbers.
"""
from __future__ import annotations

import json

from loguru import logger
from pydantic import BaseModel, Field

from llm.nemotron import NemotronClient
from models.outputs import EquivalenceReport, MigrationResult
from utils.codecheck import module_name, sanitize_python, syntax_error
from utils.equivalence import RESULT_SHAPE, compare, hardcoded_values, run_adapter, structural_problems

VERIFIER_SYSTEM = """You write a small Python adapter that drives already-migrated code \
through a fixed business scenario. Return raw Python only (no markdown, no prose).

The adapter must define:
    def run_scenario(scenario: dict) -> dict

It must: create the accounts in scenario["accounts"] using the migrated code, process
scenario["transactions"] in order using the migrated code, report balances, then run the
migrated interest posting with scenario["interest"] parameters and report again.
Use only the Python standard library and the migrated modules listed. Never compute
business results yourself and never hard-code expected numbers: call the migrated code.
Return money values as strings with two decimals and dict keys as account number strings
without leading zeros.
"""


class AdapterCode(BaseModel):
    code: str = Field(..., description="Full Python source of equivalence_adapter.py")
    notes: str = Field(default="")


async def run(
    client: NemotronClient,
    migrations: list[MigrationResult],
    scenario: dict,
    golden: dict,
    max_attempts: int = 3,
) -> EquivalenceReport:
    modules = {m.target_file: m.migrated_code for m in migrations}
    code_block = "\n\n".join(
        f"=== {m.target_file} (import as `{module_name(m.target_file)}`) ===\n{m.migrated_code}"
        for m in migrations
    )
    base_prompt = f"""Migrated modules:
{code_block}

Scenario (passed to run_scenario as a dict):
{json.dumps(scenario, indent=2)}

run_scenario must return exactly this shape:
{json.dumps(RESULT_SHAPE, indent=2)}

Legacy behaviour to respect: transactions with an unknown type, a missing account, or
insufficient funds count as failed; interest is credited only to active savings accounts.
"""
    feedback, last_error, adapter = "", None, ""
    for attempt in range(1, max_attempts + 1):
        out = await client.call(
            prompt=base_prompt + feedback, tier="nano", system=VERIFIER_SYSTEM,
            response_model=AdapterCode, max_tokens=6000, temperature=0.2,
        )
        adapter = sanitize_python(out.code)
        problems = []
        if err := syntax_error(adapter):
            problems.append(f"SyntaxError at {err}")
        if "def run_scenario" not in adapter:
            problems.append("run_scenario is not defined")
        if hard := hardcoded_values(adapter, golden):
            problems.append("hard-codes result values " + ", ".join(hard) + "; call the migrated code instead")
        actual = None
        if not problems:
            actual, last_error = run_adapter(modules, adapter, scenario)
            if last_error:
                problems.append("adapter crashed:\n" + last_error)
            elif actual is not None:
                problems.extend(structural_problems(actual, scenario))
        if not problems and actual is not None:
            checks = compare(golden, actual)
            matched = sum(c["match"] for c in checks)
            logger.success("verifier.done attempt={} matched={}/{}", attempt, matched, len(checks))
            return EquivalenceReport(adapter_code=adapter, attempts=attempt, checks=checks,
                                     matched=matched, total=len(checks), error=None)
        logger.warning("verifier: attempt {} rejected: {}", attempt, [p[:300] for p in problems])
        last_error = "; ".join(problems)
        feedback = "\n\nYour previous adapter was rejected:\n" + last_error[-2000:] + "\nReturn a corrected adapter."
    # Out of attempts: still score the last adapter that ran, and say why it was rejected.
    checks = compare(golden, actual or {})
    return EquivalenceReport(adapter_code=adapter, attempts=max_attempts, checks=checks,
                             matched=sum(c["match"] for c in checks), total=len(checks),
                             error=last_error)
