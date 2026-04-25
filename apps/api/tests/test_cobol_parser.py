"""Test the COBOL skeleton extractor on real banking samples."""
from pathlib import Path

from parsers.cobol import extract_cobol_skeleton

SAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples" / "cobol-banking"


def test_account_skeleton():
    src = (SAMPLES_DIR / "ACCOUNT.cbl").read_text(encoding="utf-8")
    skel = extract_cobol_skeleton("ACCOUNT.cbl", src)
    assert "PROGRAM-ID: ACCOUNT" in skel
    assert "MAIN-LOGIC" in skel
    assert "CREATE-ACCOUNT" in skel
    assert "QUERY-ACCOUNT" in skel
    assert "ACCOUNT-FILE" in skel


def test_transact_has_three_transaction_types():
    src = (SAMPLES_DIR / "TRANSACT.cbl").read_text(encoding="utf-8")
    skel = extract_cobol_skeleton("TRANSACT.cbl", src)
    assert "POST-DEPOSIT" in skel
    assert "POST-WITHDRAW" in skel
    assert "POST-TRANSFER" in skel


def test_interest_includes_compound_logic():
    src = (SAMPLES_DIR / "INTEREST.cbl").read_text(encoding="utf-8")
    skel = extract_cobol_skeleton("INTEREST.cbl", src)
    assert "COMPUTE-PERIOD-RATE" in skel
    assert "CREDIT-INTEREST" in skel


def test_skeleton_handles_unknown_extension():
    src = "       PROGRAM-ID. FOO.\n       PROCEDURE DIVISION.\n       MAIN. STOP RUN."
    skel = extract_cobol_skeleton("foo.cbl", src)
    assert "PROGRAM-ID: FOO" in skel
