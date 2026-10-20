"""Offline checks of the golden-file harness, using a hand-written reference port."""
from pathlib import Path

from utils.equivalence import compare, hardcoded_values, load_golden, run_adapter

GOLDEN_DIR = Path(__file__).resolve().parents[3] / "tools" / "golden"

REFERENCE_BANK = '''
from decimal import Decimal, ROUND_DOWN

class Bank:
    def __init__(self):
        self.accts = {}
    def create(self, number, holder, kind, deposit):
        self.accts[number] = {"type": kind, "balance": Decimal(deposit), "status": "A"}
    def post(self, t):
        a, amt = self.accts, Decimal(t["amount"])
        if t["type"] == "DP" and t["to"] in a:
            a[t["to"]]["balance"] += amt; return True
        if t["type"] == "WD" and t["from"] in a and a[t["from"]]["balance"] >= amt:
            a[t["from"]]["balance"] -= amt; return True
        if t["type"] == "TF" and t["from"] in a and a[t["from"]]["balance"] >= amt:
            a[t["from"]]["balance"] -= amt          # legacy: debit kept even if target missing
            if t["to"] in a:
                a[t["to"]]["balance"] += amt; return True
        return False
    def interest(self, rate, periods, years):
        q9 = Decimal("0.000000001")
        i = (Decimal(rate) / periods).quantize(q9, ROUND_DOWN)
        f = Decimal(1)
        for _ in range(periods * years):
            f = (f * (1 + i)).quantize(q9, ROUND_DOWN)
        credited = {}
        for n in sorted(self.accts):
            r = self.accts[n]
            if r["type"] == "SV" and r["status"] == "A":
                new = (r["balance"] * f).quantize(Decimal("0.01"), ROUND_DOWN)
                credited[n] = new - r["balance"]; r["balance"] = new
        return credited
'''

REFERENCE_ADAPTER = '''
from bank.core import Bank

def run_scenario(s):
    b = Bank()
    for a in s["accounts"]:
        b.create(a["number"], a["holder"], a["type"], a["deposit"])
    ok = [b.post(t) for t in s["transactions"]]
    bal = lambda: {str(n): f"{r['balance']:.2f}" for n, r in b.accts.items()}
    after_t = bal()
    p = s["interest"]
    cr = b.interest(p["annual_rate"], p["periods_per_year"], p["years"])
    return {"transact": {"processed": sum(ok), "failed": len(ok) - sum(ok), "balances_after": after_t},
            "interest": {"credited": {str(k): f"{v:.2f}" for k, v in cr.items()},
                         "total_interest": f"{sum(cr.values()):.2f}", "accounts_credited": len(cr),
                         "accounts_read": len(b.accts), "balances_after": bal()}}
'''


def test_reference_port_matches_cobol_golden():
    scenario, golden = load_golden(GOLDEN_DIR)
    actual, err = run_adapter({"bank/core.py": REFERENCE_BANK}, REFERENCE_ADAPTER, scenario)
    assert err is None, err
    checks = compare(golden, actual)
    assert [c for c in checks if not c["match"]] == []
    assert len(checks) == 5 + 5 + 3 + 5


def test_empty_result_is_all_mismatch():
    _, golden = load_golden(GOLDEN_DIR)
    assert not any(c["match"] for c in compare(golden, {}))


def test_hardcoded_values_detected():
    _, golden = load_golden(GOLDEN_DIR)
    assert hardcoded_values('return {"total_interest": "229.69"}', golden) == ["229.69"]


def test_structural_problems_flags_unprocessed_transactions():
    from utils.equivalence import structural_problems

    scenario, _ = load_golden(GOLDEN_DIR)
    probs = structural_problems({"transact": {"processed": 0, "failed": 0}}, scenario)
    assert any("processed + failed" in p for p in probs)


def test_money_with_commas_compares_equal():
    from utils.equivalence import _eq

    assert _eq("1150.75", "1,150.75") and _eq("1000.00", "$1,000.00")
