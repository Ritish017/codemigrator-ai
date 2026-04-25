"""
READER agent — runs on Nemotron 3 Nano.

Pre-parses files with tree-sitter (when available) for deterministic structure,
then asks Nano to enrich with semantic context.
"""
from __future__ import annotations

from loguru import logger

from llm.nemotron import NemotronClient
from llm.prompts import READER_SYSTEM
from models.outputs import CodebaseAnalysis
from models.state import SourceFile
from parsers.cobol import extract_cobol_skeleton


async def run(client: NemotronClient, source_files: list[SourceFile]) -> CodebaseAnalysis:
    logger.info("reader.start files={}", len(source_files))

    # Deterministic skeleton extraction first.
    skeletons: list[str] = []
    for sf in source_files:
        if sf["language"].lower() == "cobol":
            skeleton = extract_cobol_skeleton(sf["path"], sf["content"])
        else:
            skeleton = f"# {sf['path']}\n{sf['content'][:2000]}"
        skeletons.append(skeleton)

    files_block = "\n\n".join(
        f"=== FILE: {sf['path']} ({sf['language']}, {len(sf['content'].splitlines())} lines) ===\n"
        f"{sf['content']}"
        for sf in source_files
    )
    skel_block = "\n\n".join(skeletons)

    prompt = f"""Analyze the following legacy codebase and return a structured CodebaseAnalysis.

Pre-extracted skeletons (deterministic AST summary, trust these):
{skel_block}

Full source for semantic enrichment:
{files_block}

Produce a thorough analysis. Be specific — name actual paragraphs, files, and modules.
Map dependencies based on CALL statements, COPY statements, and shared file references.
"""

    analysis = await client.call(
        prompt=prompt,
        tier="nano",
        system=READER_SYSTEM,
        response_model=CodebaseAnalysis,
        max_tokens=4096,
    )
    logger.success(
        "reader.done modules={} complexity={}",
        len(analysis.modules),
        analysis.estimated_complexity,
    )
    return analysis
