# Benchmarks

> **TBD — to be populated after the first end-to-end live run** against
> `examples/cobol-banking/` (3 files, ~250 LOC) on the NVIDIA NIM free tier.
>
> The numbers below are not measurements yet. Run the demo, capture actuals, and replace.

## Pipeline latency

| Stage         | Tier  | Latency (median) |
| ------------- | ----- | ---------------- |
| Reader        | Nano  | _TBD_            |
| Architect     | Super | _TBD_            |
| Migrator      | Nano  | _TBD_            |
| Tester        | Super → Nano | _TBD_     |
| Documenter    | Nano  | _TBD_            |
| **End-to-end**|       | _TBD_            |

## Token usage

| Agent       | Calls | Total tokens (in+out) |
| ----------- | ----- | --------------------- |
| Reader      | 1     | _TBD_                 |
| Architect   | 1     | _TBD_                 |
| Migrator    | N     | _TBD_                 |
| Tester      | 2     | _TBD_                 |
| Documenter  | 1     | _TBD_                 |
| **Total**   |       | _TBD_                 |

## Routing distribution (deterministic from architecture)

For the bundled 3-file sample the call counts are structural:

- 1 Reader (Nano) + 1 Architect (Super) + 3 Migrator (Nano, parallel)
  + 2 Tester (1 Super, 1 Nano) + 1 Documenter (Nano)
- = **6 Nano / 8 total = 75% Nano**, **2 Super / 8 total = 25% Super**

That ratio holds regardless of file count for the non-Migrator agents; the Migrator's
N parallel Nano calls only push the Nano percentage higher on bigger codebases.

## Cost

NVIDIA hasn't published per-token pricing for these specific NIM-hosted models, so the
metrics card surfaces token counts only. The free tier is free; cost is left blank
until a verified production rate is confirmed.

## Quality

| Metric                                      | Value |
| ------------------------------------------- | ----- |
| Files migrated successfully                 | _TBD_ |
| Average migration confidence (self-reported)| _TBD_ |
| Tests generated                             | _TBD_ |

## How to reproduce

```bash
cp .env.example .env  # add NVIDIA_API_KEY
make setup
make run-api     # in one terminal
make run-web     # in another, then open http://localhost:3000
```

Click "Try Sample COBOL Banking". The metrics card surfaces tokens and routing
distribution live.
