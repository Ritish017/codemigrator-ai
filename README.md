# CodeMigrator AI

> **Multi-agent legacy code migration powered by NVIDIA Nemotron 3** — Super + Nano routing,
> end-to-end COBOL → Python in seconds. Built for the NVIDIA Nemotron 3 Workshop at
> IIIT Hyderabad, May 16 2026.

[![Powered by NVIDIA Nemotron](https://img.shields.io/badge/Powered%20by-NVIDIA%20Nemotron%203-76B900?style=flat-square)](https://build.nvidia.com)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)](https://nextjs.org/)

---

## What it does

You upload legacy code (COBOL, Fortran, PL/I…). Five specialist agents collaborate via
LangGraph to migrate it to a modern target language with idiomatic architecture, tests,
and a migration report. Heavy reasoning runs on **Nemotron 3 Super (120B, 1M ctx)**;
high-throughput conversion runs on **Nemotron 3 Nano (30B)**.

**No other LLM provider is used.** This is a Nemotron-only project — the kind of demo
NVIDIA engineers actually want to see.

## The 5 agents

| Agent       | Tier        | Job                                                            |
| ----------- | ----------- | -------------------------------------------------------------- |
| Reader      | Nano        | Parse AST, identify dependencies, summarize the codebase       |
| Architect   | Super       | Design the target architecture in a single 1M-context pass     |
| Migrator    | Nano (×N)   | Convert files in parallel, following the architectural plan    |
| Tester      | Super → Nano| Strategy on Super, pytest cases on Nano                        |
| Documenter  | Nano        | Synthesize the full Markdown migration report                  |

## Quick start

### 1. Get a free NVIDIA API key

Sign up at <https://build.nvidia.com>. The free tier gives you 1,000 inference credits and
40 req/min — enough for the demo. Your key starts with `nvapi-`.

### 2. Configure

```bash
cp .env.example .env
# Edit .env and paste your NVIDIA_API_KEY=nvapi-...
```

### 3. Install

```bash
make setup           # installs Python and Node deps
```

### 4. Run

```bash
make run-api         # terminal 1 — http://localhost:8000
make run-web         # terminal 2 — http://localhost:3000
```

Open <http://localhost:3000> and click **"Try Sample COBOL Banking"** for a one-click
demo on three real banking COBOL programs.

## Project layout

```
codemigrator-ai/
├── apps/
│   ├── api/             # 100% Python: FastAPI + LangGraph + Pydantic v2 + Nemotron
│   │   ├── llm/         # Nemotron client (the only LLM module)
│   │   ├── agents/      # Reader · Architect · Migrator · Tester · Documenter
│   │   ├── parsers/     # COBOL skeleton extractor
│   │   ├── models/      # Pydantic output schemas + LangGraph state
│   │   ├── routes/      # /api/migrate (SSE) + /api/health + /api/sample
│   │   └── tests/       # Smoke + structure tests
│   └── web/             # Next.js 14 + Tailwind + Framer Motion + Monaco diff
├── examples/cobol-banking/   # ACCOUNT.cbl · TRANSACT.cbl · INTEREST.cbl
└── docs/                # ARCHITECTURE.md · DEMO.md · BENCHMARKS.md
```

## Key technical choices

- **NVIDIA NIM is OpenAI-compatible.** We use the `openai` Python SDK with
  `base_url="https://integrate.api.nvidia.com/v1"`. No `anthropic` SDK, no other providers.
- **Structured outputs via JSON-schema injection.** Every agent returns a Pydantic v2 model.
  We append the model's `model_json_schema()` to the prompt and parse + validate the response.
- **Asyncio semaphore (15 concurrent)** keeps us safely under the 40 req/min free-tier ceiling.
- **LangGraph + SSE** for streaming agent progress — every state change becomes one server-sent
  event, the React client renders the timeline live.
- **Monaco diff editor** for before/after code views.

## Demo metrics

For the bundled 3-file COBOL banking sample, the call distribution is deterministic
from the architecture:

- 1 Reader (Nano) + 1 Architect (Super) + 3 Migrator (Nano) + 2 Tester (1 Super, 1 Nano) + 1 Documenter (Nano)
- = 8 Nemotron calls, **6 of them on Nano → 75% routed to Nano** (the headline metric)

Live token counts and latency are surfaced by the UI metrics card per run. Per-token
pricing for these specific NIM-hosted models isn't publicly published, so the cost
field is reported as $0 (free tier) until a verified rate is confirmed.

See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for the live numbers once captured.

## Tests

```bash
make test                  # unit tests (no API key needed)
make smoke                 # live Nemotron smoke test (needs NVIDIA_API_KEY)
```

## Docker

```bash
docker-compose up --build
```

## Author

**Ritish Kurma**  
[LinkedIn](https://www.linkedin.com/in/ritish-kurma/) ·
kurmaritish017@gmail.com

Built for the NVIDIA Nemotron 3 Workshop · IIIT Hyderabad · May 16 2026.

## License

MIT — go build cool things.
