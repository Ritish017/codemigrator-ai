"""Run the legacy COBOL sample under GnuCOBOL on a fixed scenario and record golden outputs.

    python tools/golden/run_golden.py            # writes tools/golden/golden.json

Requires `cobc` (GnuCOBOL 3.x with an indexed-file handler, e.g. BDB) on PATH.
The outputs are produced by the original programs, never by an LLM, so they are the
reference the migrated code must match.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = ROOT / "examples" / "cobol-banking"


def pack_comp3(value: Decimal, digits: int = 13, scale: int = 2) -> bytes:
    """PIC S9(11)V99 COMP-3: 13 digits + sign nibble = 7 bytes."""
    n = int((abs(value) * (10 ** scale)).to_integral_value())
    s = str(n).rjust(digits, "0") + ("D" if value < 0 else "C")
    if len(s) % 2:
        s = "0" + s
    return bytes.fromhex(s)


def trans_record(t: dict) -> bytes:
    rec = (
        str(t["id"]).rjust(10, "0").encode()
        + t["type"].ljust(2)[:2].encode()
        + str(t["from"]).rjust(10, "0").encode()
        + str(t["to"]).rjust(10, "0").encode()
        + pack_comp3(Decimal(t["amount"]))
        + "20261020120000".encode()
    )
    assert len(rec) == 53, len(rec)
    return rec


def money(text: str) -> str:
    return str(Decimal(text.replace("$", "").replace(",", "").strip() or "0"))


def run(exe: Path, cwd: Path, stdin: str = "") -> str:
    r = subprocess.run([str(exe)], input=stdin, cwd=cwd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"{exe.name} failed: {r.stderr}")
    return r.stdout


def query_balances(work: Path, accounts: list[dict]) -> dict[str, str]:
    out = {}
    for a in accounts:
        text = run(work / "ACCOUNT", work, f"Q\n{a['number']:010d}\n")
        m = re.search(r"BALANCE:\s*(\S+)", text)
        out[str(a["number"])] = money(m.group(1)) if m else "NOT FOUND"
    return out


def main() -> int:
    if not shutil.which("cobc"):
        print("cobc (GnuCOBOL) not found on PATH", file=sys.stderr)
        return 2
    scenario = json.loads((HERE / "scenario.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for prog, path in [("ACCOUNT", SRC / "ACCOUNT.cbl"), ("INTEREST", SRC / "INTEREST.cbl"),
                           ("TRANSACT", SRC / "TRANSACT.cbl"), ("INITACCT", HERE / "INITACCT.cbl")]:
            subprocess.run(["cobc", "-x", "-free", "-o", str(work / prog), str(path)], check=True)

        run(work / "INITACCT", work)
        for a in scenario["accounts"]:
            out = run(work / "ACCOUNT", work,
                      f"C\n{a['number']:010d}\n{a['holder']}\n{a['type']}\n{a['deposit']}\n")
            assert "ACCOUNT CREATED SUCCESSFULLY" in out, out
        opening = query_balances(work, scenario["accounts"])

        (work / "TRANS.DAT").write_bytes(b"".join(trans_record(t) for t in scenario["transactions"]))
        # TRANSACT opens AUDIT.LOG with OPEN EXTEND, which needs the file to exist.
        (work / "AUDIT.LOG").write_text("")
        tout = run(work / "TRANSACT", work)
        processed = int(re.search(r"PROCESSED:\s*(\d+)", tout).group(1))
        failed = int(re.search(r"FAILED:\s*(\d+)", tout).group(1))
        audit = [ln.rstrip() for ln in (work / "AUDIT.LOG").read_text().splitlines() if ln.strip()]
        after_transact = query_balances(work, scenario["accounts"])

        run(work / "INTEREST", work)
        report = [ln.rstrip() for ln in (work / "INTEREST.RPT").read_text().splitlines() if ln.strip()]
        credited = {}
        for ln in report:
            if m := re.match(r"ACC=(\d{10}) HOLDER=.{40} INTEREST=\s*(\S+)", ln):
                credited[str(int(m.group(1)))] = money(m.group(2))
        # Report lines are built with STRING into a buffer that is never cleared, so
        # leftover text from the previous line trails each one (a legacy quirk, recorded
        # in "legacy_quirks"). Parse only the fixed-width leading fields.
        total_ln = next((ln for ln in report if ln.startswith("TOTAL INTEREST")), "")
        total = money(re.search(r"CREDITED:\s*(\$[\d,]+\.\d\d)", total_ln).group(1))
        counts = next((ln for ln in report if ln.startswith("ACCOUNTS CREDITED")), "")
        cm = re.search(r"CREDITED:\s*(\d{7})\s*/\s*READ:\s*(\d{7})", counts)
        after_interest = query_balances(work, scenario["accounts"])

    golden = {
        "generated_by": "tools/golden/run_golden.py (GnuCOBOL, original COBOL sources)",
        "legacy_quirks": [
            "TRANSACT and INTEREST build output lines with STRING into a buffer that is never "
            "cleared, so shorter lines carry trailing text from the previous line.",
            "POST-TRANSFER debits the source account before checking the destination exists; "
            "a transfer to a missing account is counted as failed but the debit is kept.",
            "TRANSACT originally did not compile under GnuCOBOL (STRING of a COMP-3 field); the "
            "sample now edits the amount through WS-DISPLAY-AMT first.",
        ],
        "opening_balances": opening,
        "transact": {"processed": processed, "failed": failed,
                     "balances_after": after_transact, "audit_lines": audit},
        "interest": {"credited": credited, "total_interest": total,
                     "accounts_credited": int(cm.group(1)), "accounts_read": int(cm.group(2)),
                     "balances_after": after_interest, "report_lines": report},
    }
    (HERE / "golden.json").write_text(json.dumps(golden, indent=2) + "\n")
    print(json.dumps({k: v for k, v in golden.items() if k != "generated_by"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
