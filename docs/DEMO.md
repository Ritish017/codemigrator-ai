# 5-Minute Demo Script

**Audience:** NVIDIA engineers (incl. Megh Makwana), workshop participants at IIIT Hyderabad.
**Goal:** Show that real Super + Nano routing produces real ROI on a real legacy task.
**Setup:** Browser at `http://localhost:3000`, terminal visible alongside for the API logs.

---

## 0:00 — Opening (30s)

> "Hi, I'm Ritish Kurma. Most enterprises are sitting on millions of lines of COBOL
> they want to retire — but rewriting it manually costs millions and takes years.
> Today I'll show you **CodeMigrator AI** — a multi-agent system that migrates COBOL to
> modern Python automatically, running 100% on **NVIDIA Nemotron 3**."

*[Show landing page with the green "Powered by NVIDIA Nemotron 3" badge]*

## 0:30 — The architecture (45s)

> "Five specialist agents collaborate via LangGraph. Each runs on the right tier of
> Nemotron — heavy reasoning on **Super 120B**, high-throughput conversion on **Nano 30B**.
> That's the Super + Nano routing pattern NVIDIA's been talking about, applied to a real
> enterprise problem."

*[Point at the timeline on the left, showing the 5 agents with tier badges]*

## 1:15 — Click "Try Sample COBOL Banking" (1m)

> "Three real banking COBOL programs — account maintenance, transaction processing, and
> compound interest calculation. About 250 lines of mainframe code with file I/O,
> PERFORM-VARYING loops, packed-decimal arithmetic — the works."

*[Click the green button. Watch the timeline light up.]*

> "**Reader** — running on Nano — is parsing the AST and identifying dependencies. Done in
> about 2 seconds. Now **Architect** — this is the star — it's a Super call. We're feeding
> the entire codebase plus the Reader's analysis into a single 120B reasoning pass."

*[Architect's "thinking" pane streams in real-time as Super reasons.]*

## 2:15 — Architect output (45s)

> "Look at the rationale Super produced. It picked FastAPI + SQLAlchemy 2.0 async,
> mapped the indexed COBOL files to a repository pattern, and explicitly flagged the
> packed-decimal types as needing `Decimal` instead of `float`. That kind of architectural
> reasoning is exactly what the 1M-token context unlocks — Super sees the whole codebase
> at once, not chunked."

## 3:00 — Migrator runs in parallel (1m)

> "Now **Migrator** kicks off three parallel Nano calls — one per file. Watch the diff
> view fill in. Notice the type-hinted Python, async I/O, Pydantic models for the
> records, and `Decimal` for monetary values — exactly what the Architect specified."

*[Switch tabs in the diff view, point out converted PERFORM-VARYING → for-range loop.]*

## 4:00 — Tests + report (45s)

> "**Tester** — Super designs the strategy, Nano writes pytest cases. **Documenter** —
> Nano synthesizes a markdown report covering everything: architecture, file map, risks,
> Nemotron usage."

## 4:45 — The metrics (15s)

> "Here's the punchline. Look at the routing card: **most of the calls go to Nano** —
> only the architectural reasoning needed Super. That's the Super + Nano routing
> pattern in action: send the rare hard-thinking task to the big model, keep everything
> else on the cheap fast model. **That's the payoff.**"

*[Point at the green "Routed to Nano: X%" stat — the live number from this run]*

> "Repo and slides are linked in the footer. Thanks!"

---

## Backup slides if API is rate-limited

1. Pre-recorded video of the same demo (record before the workshop).
2. Screenshot tour of the metrics card with annotations.
3. Architecture diagram from `docs/ARCHITECTURE.md`.
