"""
Migration route — POST /api/migrate streams agent progress over SSE.
Also exposes /api/sample for one-click demo.
"""
from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from agents.orchestrator import stream_migration
from llm.nemotron import get_client
from llm.streaming import (
    agent_complete,
    complete_event,
    error_event,
    metrics_update,
    progress,
)
from models.state import SourceFile

router = APIRouter()


# Map agent node name -> (display name, percent, summary suffix).
NODE_LABELS = {
    "reader": ("Reader", 20.0),
    "architect": ("Architect", 45.0),
    "migrator": ("Migrator", 75.0),
    "tester": ("Tester", 90.0),
    "documenter": ("Documenter", 100.0),
}


def _detect_language(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".cbl": "cobol",
        ".cob": "cobol",
        ".cobol": "cobol",
        ".cpy": "cobol",
        ".f": "fortran",
        ".f90": "fortran",
        ".pli": "pli",
    }.get(ext, "unknown")


async def _read_uploaded_files(files: list[UploadFile]) -> list[SourceFile]:
    out: list[SourceFile] = []
    for f in files:
        content = await f.read()
        # If they uploaded a zip, expand it.
        if f.filename and f.filename.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for member in zf.namelist():
                    if member.endswith("/"):
                        continue
                    data = zf.read(member).decode("utf-8", errors="replace")
                    out.append(
                        SourceFile(
                            path=member,
                            content=data,
                            language=_detect_language(member),
                        )
                    )
            continue

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        out.append(
            SourceFile(
                path=f.filename or "untitled",
                content=text,
                language=_detect_language(f.filename or ""),
            )
        )
    return out


def _samples_dir() -> Path:
    # examples are mounted relative to the repo root.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "examples" / "cobol-banking"
        if candidate.exists():
            return candidate
    return Path("examples/cobol-banking")


def _load_samples() -> list[SourceFile]:
    folder = _samples_dir()
    if not folder.exists():
        return []
    files: list[SourceFile] = []
    for path in sorted(folder.glob("*.cbl")):
        files.append(
            SourceFile(
                path=path.name,
                content=path.read_text(encoding="utf-8", errors="replace"),
                language="cobol",
            )
        )
    return files


@router.get("/sample")
async def sample_files() -> dict:
    """Return the bundled COBOL banking sample."""
    files = _load_samples()
    return {
        "count": len(files),
        "language": "cobol",
        "files": [
            {"path": f["path"], "lines": len(f["content"].splitlines()), "preview": f["content"][:600]}
            for f in files
        ],
    }


async def _run_pipeline_sse(
    source_files: list[SourceFile], target_language: str
) -> AsyncIterator[dict]:
    """The actual SSE stream generator."""
    client = get_client()
    client.reset_metrics()

    yield progress("init", 0.0, f"Starting migration of {len(source_files)} files")

    try:
        last_metrics: dict = {}
        async for chunk in stream_migration(source_files, target_language):
            node = chunk["node"]
            state = chunk["state"]

            if node == "error":
                yield error_event(state.get("errors", ["unknown error"])[0])
                return

            label_info = NODE_LABELS.get(node)
            if label_info:
                label, pct = label_info
                yield progress(node, pct, f"{label} agent finished")
                # Per-agent summary payloads for the timeline UI.
                summary_payload: dict = {}
                if node == "reader" and state.get("analysis") is not None:
                    a = state["analysis"]
                    summary_payload = {
                        "total_files": a.total_files,
                        "total_lines": a.total_lines,
                        "modules": [m.name for m in a.modules],
                        "complexity": a.estimated_complexity,
                        "patterns": a.patterns_detected,
                    }
                elif node == "architect" and state.get("plan") is not None:
                    p = state["plan"]
                    summary_payload = {
                        "framework": p.target_architecture.framework,
                        "files_planned": len(p.file_migration_order),
                        "modernization": p.modernization_opportunities[:5],
                        "rationale": p.architectural_rationale,
                        "estimated_effort_hours": p.estimated_effort_hours,
                    }
                elif node == "migrator" and state.get("migrations"):
                    summary_payload = {
                        "files_migrated": len(state["migrations"]),
                        "files": [
                            {
                                "source": m.source_file,
                                "target": m.target_file,
                                "code": m.migrated_code,
                                "confidence": m.confidence,
                                "warnings": m.warnings,
                            }
                            for m in state["migrations"]
                        ],
                    }
                elif node == "tester" and state.get("tests") is not None:
                    t = state["tests"]
                    summary_payload = {
                        "test_files": len(t.test_files),
                        "coverage": t.coverage_estimate,
                        "strategy": t.strategy,
                        "files": [
                            {"filename": tf.filename, "code": tf.code, "test_count": tf.test_count}
                            for tf in t.test_files
                        ],
                    }
                elif node == "documenter" and state.get("report") is not None:
                    r = state["report"]
                    summary_payload = {
                        "title": r.title,
                        "summary": r.summary,
                        "markdown": r.markdown,
                    }

                yield agent_complete(node, label, summary_payload)

            # Push metrics after each node.
            metrics = client.get_metrics()
            if metrics != last_metrics:
                yield metrics_update(metrics)
                last_metrics = metrics

        # Final completion.
        yield complete_event({"metrics": client.get_metrics()})
    except asyncio.CancelledError:
        logger.info("migrate.stream cancelled by client")
        raise
    except Exception as exc:
        logger.exception("migrate.stream failed")
        yield error_event(f"Pipeline failure: {exc}")


@router.post("/migrate")
async def migrate(
    files: list[UploadFile] = File(...),
    target_language: str = Form("python"),
):
    """Upload source files and stream migration progress as SSE."""
    source_files = await _read_uploaded_files(files)
    if not source_files:
        return JSONResponse({"error": "no files provided"}, status_code=400)

    return EventSourceResponse(_run_pipeline_sse(source_files, target_language))


@router.post("/migrate/sample")
async def migrate_sample(target_language: str = Form("python")):
    """One-click demo: stream a migration of the bundled COBOL banking files."""
    source_files = _load_samples()
    if not source_files:
        return JSONResponse({"error": "no sample files bundled"}, status_code=500)
    return EventSourceResponse(_run_pipeline_sse(source_files, target_language))
