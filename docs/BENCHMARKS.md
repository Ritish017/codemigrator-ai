# Benchmarks

Live runs on **2026-10-19/20**, NVIDIA NIM free tier, against `examples/cobol-banking/`
(ACCOUNT.cbl, INTEREST.cbl, TRANSACT.cbl: 3 files, 390 lines). Measured with
`apps/api/bench_run.py`, which runs the full pipeline, writes the migrated package to
`bench_out/migrated/`, and **executes the generated pytest suite** against it.

Models: Super = `nvidia/nemotron-3-super-120b-a12b`, Nano tier =
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

## Run history

| Run | Change | Modules | Tests run | Passing |
| --- | ------ | ------- | --------- | ------- |
| 1 | Model swap + JSON parser fix | 3 | 0 (syntax errors) | 0 |
| 2 | Self-contained architecture, code sanitizer, import checks | 4 | 27 | 10 |
| 3 | + undefined-name check, larger Tester budget | 6 | 0 (migrated module import error) | 0 |
| 4 | + import-check and re-migrate pass, execution check in Tester | 5 | 35 | 11 |

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

1. Golden-file equivalence: run the original COBOL under GnuCOBOL on fixed inputs and
   compare outputs with the Python, instead of relying on LLM-written assertions.
2. Give the Tester the public signatures of each module (extracted with `ast`) rather than
   full source, to cut interface mismatches.
3. Use JSON-mode / structured output on NIM to remove the remaining invalid-JSON retries.

## Reproduce

```bash
cp .env.example .env  # add NVIDIA_API_KEY
make setup-api
cd apps/api && python bench_run.py   # writes bench_out/results.json
```
