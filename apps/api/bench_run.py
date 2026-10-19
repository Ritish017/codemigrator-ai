"""Benchmark run: full pipeline on examples/cobol-banking, then execute generated tests."""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from agents.orchestrator import stream_migration
from llm.nemotron import get_client
from routes.migrate import _load_samples

OUT = Path(__file__).parent / "bench_out"

async def main():
    OUT.mkdir(exist_ok=True)
    files = _load_samples()
    client = get_client(); client.reset_metrics()
    t0 = time.perf_counter(); last = t0
    stages, state = {}, {}
    async for ch in stream_migration(files, "python"):
        now = time.perf_counter()
        if ch["node"] == "error":
            print("ERROR", ch["state"]); state["error"] = ch["state"]; break
        stages[ch["node"]] = round(now - last, 1); last = now
        state.update(ch["state"])
    total = round(time.perf_counter() - t0, 1)
    res = {"source_files": [f["path"] for f in files],
           "source_lines": sum(len(f["content"].splitlines()) for f in files),
           "stage_seconds": stages, "end_to_end_seconds": total,
           "metrics": client.get_metrics()}
    migs = state.get("migrations") or []
    res["files_migrated"] = len(migs)
    res["confidence"] = [getattr(m, "confidence", None) for m in migs]
    res["warnings"] = sum(len(getattr(m, "warnings", []) or []) for m in migs)
    import re, shutil
    pkg = OUT / "migrated"; shutil.rmtree(pkg, ignore_errors=True); pkg.mkdir(parents=True)
    def put(rel, text):
        p = pkg / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        for d in p.relative_to(pkg).parents:
            if str(d) != "." and not (pkg / d / "__init__.py").exists():
                (pkg / d / "__init__.py").write_text("")
    for m in migs:
        put(m.target_file, m.migrated_code)
    t = state.get("tests")
    if t:
        res["test_files"] = len(t.test_files)
        res["tests_declared"] = sum(tf.test_count for tf in t.test_files)
        res["coverage_estimate_self_reported"] = t.coverage_estimate
        for tf in t.test_files:
            put(Path("tests_generated") / Path(tf.filename).name, tf.code)
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "--rootdir", str(pkg), "--tb=line", "tests_generated"],
                           capture_output=True, text=True, cwd=pkg, timeout=300,
                           env={**os.environ, "PYTHONPATH": str(pkg)})
        res["pytest_tail"] = r.stdout[-2500:]
        summary = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        res["pytest_summary"] = summary
        for k in ("passed", "failed", "error", "errors"):
            mm = re.search(rf"(\d+) {k}\b", summary)
            if mm: res[f"tests_{k}"] = int(mm.group(1))
    if state.get("report") is not None:
        (OUT / "report.md").write_text(state["report"].markdown)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=2, default=str))

asyncio.run(main())
