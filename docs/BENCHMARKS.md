# Benchmarks

Live runs on **2026-10-19/20**, NVIDIA NIM free tier, against `examples/cobol-banking/`
(ACCOUNT.cbl, INTEREST.cbl, TRANSACT.cbl: 3 files, 390 lines). Measured with
`apps/api/bench_run.py`, which runs the full pipeline, writes the migrated package to
`bench_out/migrated/`, and **executes the generated pytest suite** against it.

Models: Super = `nvidia/nemotron-3-super-120b-a12b` (runs 1-4) and
`nvidia/nemotron-3.5-super-vl-120b-a12b` (runs 5-6, after the former began returning
HTTP 404 for this key on 2026-10-20), Nano tier =
`nvidia/nemotron-3.5-lightning-30b-a3b` (reasoning off on both by default; set
`NEMOTRON_SUPER_THINKING=1` to enable it on Super). The original Nano model,
`nvidia/nemotron-3-nano-30b-a3b`, was retired by NVIDIA on 2026-09-01 (HTTP 410).

## Latest run (with validation loops)

| Stage       | Tier          | Seconds |
| ----------- | ------------- | ------- |
| Reader      | Nano          | 10.3    |
| Architect   | Super         | 49.5    |
| Migrator    | Nano          | 333.2   |
| Tester      | Super -> Nano | 187.7   |
| Documenter  | Nano          | 34.0    |
| **End-to-end** |            | **614.7** |

| Metric                         | Value |
| ------------------------------ | ----- |
| LLM calls                      | 23 (2 Super, 21 Nano; 91.3% Nano) |
| Tokens                         | 136,660 (Super 10,027 / Nano 126,633) |
| Avg call latency               | Super 25.9 s, Nano 26.1 s |
| Target modules generated       | 5 / 5 planned |
| Generated tests executed       | 35 |
| **Generated tests passing**    | **11 / 35 (31%)** |

Latency includes free-tier queueing and retries, and varies a lot run to run
(end-to-end 523 s to 998 s across the four completed runs).

## Golden-file equivalence (added 2026-10-20)

`tools/golden/` runs the **original COBOL under GnuCOBOL 3.2** on a fixed scenario
(5 accounts, 9 transactions covering deposits, withdrawals, transfers, insufficient funds,
unknown accounts and an invalid type, then one year of monthly interest) and records
18 reference values in `golden.json`: processed/failed counts, every balance after
TRANSACT, interest per account, total interest, and every balance after INTEREST.

The new **Verifier** stage asks Nano for a small adapter that drives the migrated modules
through that scenario. Fixed code compares the adapter's output with the golden values.
The model never writes the assertions, hard-coded expected values are rejected, and only
crashes or structural gaps (a transaction not counted, an account not reported) are fed
back; mismatches never are.

Harness check: a hand-written reference port (`apps/api/tests/test_equivalence.py`)
matches **18/18**, so the harness and the golden values agree with each other.

| Run | Modules | Generated tests passing | Golden equivalence |
| --- | ------- | ----------------------- | ------------------ |
| 5 | 5 | 29 / 35 | **1 / 18**: adapter ran but no transaction reached the migrated code |
| 6 | 7 | 0 (collection error) | **0 / 18**: adapter crashed on all 3 attempts |

So the honest status today: the generated code is **not yet shown to be equivalent** to
the COBOL. In run 5 the interest arithmetic was in the right range (5,000.00 at 4.5%
monthly gave 229.70 interest; COBOL truncates intermediate factors), but balances never
reflected the transactions. Note that a high self-written test pass rate (29/35 in run 5)
coexisted with 1/18 on golden values, which is exactly why the golden check exists.

### Legacy bugs the harness surfaced in the sample COBOL
- `TRANSACT.cbl` did not compile under GnuCOBOL (STRING of a COMP-3 field). Fixed by
  editing the amount through the already-declared `WS-DISPLAY-AMT`.
- `POST-TRANSFER` debits the source account before checking the destination exists, so a
  transfer to a missing account is counted as failed **but the money is still debited**
  (account 105 in the scenario loses 50.00). The golden file keeps this behaviour, since a
  migration must reproduce it or flag it.
- Report and audit lines are built with STRING into buffers that are never cleared, so
  shorter lines carry trailing text from the previous line.

## Run history

| Run | Change | Modules | Tests run | Passing |
| --- | ------ | ------- | --------- | ------- |
| 1 | Model swap + JSON parser fix | 3 | 0 (syntax errors) | 0 |
| 2 | Self-contained architecture, code sanitizer, import checks | 4 | 27 | 10 |
| 3 | + undefined-name check, larger Tester budget | 6 | 0 (migrated module import error) | 0 |
| 4 | + import-check and re-migrate pass, execution check in Tester | 5 | 35 | 11 |
| 5 | + Verifier (golden equivalence), Super 3.5 | 5 | 35 | 29 |
| 6 | + structural checks on adapter output | 7 | 0 (collection error) | 0 |

## What the numbers say

- The pipeline now completes reliably and every run produces importable, standard-library
  Python plus a pytest suite that actually executes.
- **The generated tests are not yet a trustworthy equivalence check.** Most failures are
  test/code interface mismatches (wrong constructor arguments, names imported from the
  wrong module), not confirmed behavioural bugs in the migration.
- Model-reported confidence (0.93 to 0.95) and coverage (0.88) do not match the measured
  pass rate, so they should not be shown as quality metrics.
- Assertion failures are deliberately **not** fed back to the test writer: that would teach
  it to bend expected values toward the migrated code and defeat equivalence testing.

## Next steps

1. Feed golden *mismatch locations* (not values) back to the Migrator, e.g. "balances
   unchanged after TRANSACT", and re-migrate the module responsible.
2. Ask the Architect for a fixed public API per module so the adapter has a stable
   contract instead of guessing class and method names.
3. Give the Tester the public signatures of each module (extracted with `ast`) rather than
   full source, to cut interface mismatches.
4. Use JSON-mode / structured output on NIM to remove the remaining invalid-JSON retries.

## Reproduce

```bash
cp .env.example .env  # add NVIDIA_API_KEY
make setup-api
python tools/golden/run_golden.py    # needs GnuCOBOL (cobc) with BDB; regenerates golden.json
cd apps/api && python bench_run.py   # writes bench_out/results.json
```
