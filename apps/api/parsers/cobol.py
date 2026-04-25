"""
Lightweight COBOL skeleton extractor.

We use a regex-based parser rather than tree-sitter-cobol because the
tree-sitter COBOL grammar requires a native build step that's painful in
the Windows / free-tier demo environment. The skeleton we extract here is
"good enough" to seed the Reader agent — we identify program IDs, paragraphs,
file SELECTs, copybook references, and CALL targets. Nemotron Nano then
fills in semantic detail.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CobolSkeleton:
    file_path: str
    program_id: str = ""
    author: str = ""
    paragraphs: list[str] = field(default_factory=list)
    file_selects: list[str] = field(default_factory=list)
    copy_includes: list[str] = field(default_factory=list)
    call_targets: list[str] = field(default_factory=list)
    line_count: int = 0

    def to_text(self) -> str:
        lines = [f"# COBOL skeleton: {self.file_path}"]
        if self.program_id:
            lines.append(f"PROGRAM-ID: {self.program_id}")
        if self.author:
            lines.append(f"AUTHOR: {self.author}")
        lines.append(f"LINES: {self.line_count}")
        if self.file_selects:
            lines.append(f"FILES: {', '.join(self.file_selects)}")
        if self.copy_includes:
            lines.append(f"COPY: {', '.join(self.copy_includes)}")
        if self.call_targets:
            lines.append(f"CALLS: {', '.join(self.call_targets)}")
        if self.paragraphs:
            lines.append("PARAGRAPHS:")
            lines.extend(f"  - {p}" for p in self.paragraphs)
        return "\n".join(lines)


_PROGRAM_ID_RE = re.compile(r"^\s*PROGRAM-ID\.\s*([A-Z0-9-]+)", re.IGNORECASE | re.MULTILINE)
_AUTHOR_RE = re.compile(r"^\s*AUTHOR\.\s*(.+?)\.", re.IGNORECASE | re.MULTILINE)
_PARAGRAPH_RE = re.compile(
    r"^\s{0,7}([A-Z0-9][A-Z0-9-]*)\s*\.\s*$", re.IGNORECASE | re.MULTILINE
)
_SELECT_RE = re.compile(r"^\s*SELECT\s+([A-Z0-9-]+)", re.IGNORECASE | re.MULTILINE)
_COPY_RE = re.compile(r"^\s*COPY\s+([A-Z0-9-]+)", re.IGNORECASE | re.MULTILINE)
_CALL_RE = re.compile(r"^\s*CALL\s+['\"]([A-Z0-9-]+)['\"]", re.IGNORECASE | re.MULTILINE)

# Reserved words that look like paragraphs at column-0 but are actually section/division headers.
_RESERVED = {
    "IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE", "DIVISION",
    "WORKING-STORAGE", "FILE", "SECTION", "CONFIGURATION", "INPUT-OUTPUT",
    "FILE-CONTROL", "I-O-CONTROL", "SOURCE-COMPUTER", "OBJECT-COMPUTER",
    "SPECIAL-NAMES", "LINKAGE", "REPORT", "COMMUNICATION", "SCREEN",
    "FD", "01", "05", "10", "77", "88",
}


def extract_cobol_skeleton(file_path: str, content: str) -> str:
    """Return a textual skeleton of a COBOL source file."""
    skel = CobolSkeleton(file_path=file_path, line_count=len(content.splitlines()))

    if m := _PROGRAM_ID_RE.search(content):
        skel.program_id = m.group(1).strip().rstrip(".")
    if m := _AUTHOR_RE.search(content):
        skel.author = m.group(1).strip()

    skel.file_selects = list(dict.fromkeys(_SELECT_RE.findall(content)))
    skel.copy_includes = list(dict.fromkeys(_COPY_RE.findall(content)))
    skel.call_targets = list(dict.fromkeys(_CALL_RE.findall(content)))

    paragraphs: list[str] = []
    for m in _PARAGRAPH_RE.finditer(content):
        name = m.group(1).strip().upper()
        if name in _RESERVED or name.endswith("DIVISION") or name.endswith("SECTION"):
            continue
        if name.isdigit():
            continue
        paragraphs.append(name)
    # Dedupe while preserving order.
    seen: set[str] = set()
    skel.paragraphs = [p for p in paragraphs if not (p in seen or seen.add(p))]

    return skel.to_text()
