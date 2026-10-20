"""Golden-file equivalence: compare migrated code against outputs recorded from the
original COBOL (see tools/golden/run_golden.py).

The LLM only writes an *adapter* (`run_scenario(scenario) -> dict`) that drives the
migrated modules. Expected values come from golden.json and the comparison below is
fixed code, so the model can never choose or bend what "correct" means.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from utils.codecheck import _write_tree

# Fields the adapter must return, mirroring golden.json.
RESULT_SHAPE = {
    "transact": {
        "processed": "int",
        "failed": "int",
        "balances_after": "{account_number_str: decimal_str}",
    },
    "interest": {
        "credited": "{account_number_str: decimal_str}  (interest credited per account)",
        "total_interest": "decimal_str",
        "accounts_credited": "int",
        "accounts_read": "int",
        "balances_after": "{account_number_str: decimal_str}",
    },
}

_RUNNER = """
import json, sys, traceback
from decimal import Decimal
sys.path.insert(0, {root!r})
def _plain(o):
    if isinstance(o, Decimal): return str(o)
    if isinstance(o, dict): return {{str(k): _plain(v) for k, v in o.items()}}
    if isinstance(o, (list, tuple)): return [_plain(v) for v in o]
    return o
try:
    import equivalence_adapter
    scenario = json.load(open({scenario!r}))
    out = equivalence_adapter.run_scenario(scenario)
    print("__RESULT__" + json.dumps(_plain(out)))
except Exception:
    print("__ERROR__" + traceback.format_exc()[-1500:])
"""


def load_golden(golden_dir: str | os.PathLike) -> tuple[dict, dict]:
    d = Path(golden_dir)
    return json.loads((d / "scenario.json").read_text()), json.loads((d / "golden.json").read_text())


def run_adapter(modules: dict[str, str], adapter_code: str, scenario: dict, timeout: int = 120) -> tuple[dict | None, str | None]:
    """Run the adapter against the migrated modules in a clean temp dir."""
    with tempfile.TemporaryDirectory() as tmp:
        files = dict(modules)
        files["equivalence_adapter.py"] = adapter_code
        _write_tree(tmp, files)
        sc = Path(tmp) / "_scenario.json"
        sc.write_text(json.dumps(scenario))
        code = _RUNNER.format(root=tmp, scenario=str(sc))
        try:
            r = subprocess.run([sys.executable, "-c", code], cwd=tmp, capture_output=True,
                               text=True, timeout=timeout, env={**os.environ, "PYTHONPATH": tmp})
        except subprocess.TimeoutExpired:
            return None, f"adapter timed out after {timeout}s"
    for line in r.stdout.splitlines():
        if line.startswith("__RESULT__"):
            try:
                return json.loads(line[len("__RESULT__"):]), None
            except json.JSONDecodeError as exc:
                return None, f"adapter output was not JSON: {exc}"
    err = r.stdout.split("__ERROR__", 1)[-1] if "__ERROR__" in r.stdout else (r.stderr[-1500:] or "no output")
    return None, err.strip()


def _num(v) -> Decimal | None:
    try:
        return Decimal(str(v).replace(",", "").replace("$", "").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _eq(expected, actual) -> bool:
    if isinstance(expected, int) and not isinstance(expected, bool):
        try:
            return int(actual) == expected
        except (TypeError, ValueError):
            return False
    e, a = _num(expected), _num(actual)
    return e is not None and e == a


def compare(golden: dict, actual: dict) -> list[dict]:
    """One check per golden value. A missing field counts as a mismatch."""
    checks: list[dict] = []

    def add(field, expected, got):
        checks.append({"field": field, "expected": expected, "actual": got, "match": _eq(expected, got)})

    for section, keys in (("transact", ("processed", "failed")),
                          ("interest", ("total_interest", "accounts_credited", "accounts_read"))):
        for k in keys:
            add(f"{section}.{k}", golden[section][k], (actual.get(section) or {}).get(k))
    for section, key in (("transact", "balances_after"), ("interest", "credited"), ("interest", "balances_after")):
        got = ((actual.get(section) or {}).get(key)) or {}
        got = {str(k).lstrip("0") or "0": v for k, v in got.items()} if isinstance(got, dict) else {}
        for acct, exp in golden[section][key].items():
            add(f"{section}.{key}[{acct}]", exp, got.get(acct))
    return checks


def hardcoded_values(adapter_code: str, golden: dict) -> list[str]:
    """Golden result values that appear literally in the adapter (it must compute them)."""
    values = set()
    for section in ("transact", "interest"):
        for key in ("balances_after", "credited"):
            values.update(v for v in (golden[section].get(key) or {}).values() if v not in ("0.00", "0"))
    if golden["interest"].get("total_interest"):
        values.add(golden["interest"]["total_interest"])
    opening = set(golden.get("opening_balances", {}).values())
    return sorted(v for v in values - opening if v in adapter_code)


def structural_problems(actual: dict, scenario: dict) -> list[str]:
    """Checks derived from the scenario alone (never from golden values): every transaction
    must be counted as processed or failed, and every account must be reported."""
    problems = []
    t = actual.get("transact") or {}
    try:
        counted = int(t.get("processed", 0)) + int(t.get("failed", 0))
    except (TypeError, ValueError):
        counted = -1
    if counted != len(scenario["transactions"]):
        problems.append(
            f"processed + failed = {counted}, but the scenario has {len(scenario['transactions'])} "
            "transactions; every transaction must be run through the migrated code and counted"
        )
    accts = {str(a["number"]) for a in scenario["accounts"]}
    for section in ("transact", "interest"):
        got = set(map(str, ((actual.get(section) or {}).get("balances_after") or {}).keys()))
        if missing := accts - {g.lstrip("0") for g in got}:
            problems.append(f"{section}.balances_after is missing accounts {sorted(missing)}")
    return problems
