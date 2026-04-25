"""
Pydantic v2 output models for every Nemotron agent in the pipeline.

These are sent to Nemotron as JSON schemas and used to validate responses,
so they must be strict, well-described, and serializable.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------- Reader ----------

class ModuleInfo(BaseModel):
    name: str = Field(..., description="Program / module name (e.g. PROGRAM-ID for COBOL)")
    file_path: str = Field(..., description="Source path of the module")
    lines: int = Field(..., description="Approximate line count")
    purpose: str = Field(..., description="One-sentence description of what this module does")
    key_procedures: list[str] = Field(
        default_factory=list, description="Major paragraphs / functions inside the module"
    )
    inputs: list[str] = Field(default_factory=list, description="External inputs (files, params)")
    outputs: list[str] = Field(default_factory=list, description="External outputs")


class CodebaseAnalysis(BaseModel):
    total_files: int
    total_lines: int
    modules: list[ModuleInfo]
    dependencies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Adjacency list mapping module name -> modules it depends on",
    )
    patterns_detected: list[str] = Field(
        default_factory=list,
        description="High-level patterns (e.g. 'sequential file processing', 'COPY-driven schema reuse')",
    )
    estimated_complexity: Literal["simple", "moderate", "complex"]
    domain_summary: str = Field(
        ..., description="What business domain this codebase serves, in one paragraph"
    )


# ---------- Architect ----------

class ArchitectureSpec(BaseModel):
    framework: str = Field(..., description="Target framework (e.g. 'FastAPI + SQLAlchemy')")
    project_structure: dict[str, str] = Field(
        default_factory=dict,
        description="Map of target file path -> short description of its role",
    )
    key_patterns: list[str] = Field(
        default_factory=list,
        description="Modern patterns we will adopt (DI, repository pattern, async I/O, etc.)",
    )
    data_layer: str = Field(..., description="How persistence is handled in the target stack")


class FileToMigrate(BaseModel):
    source_file: str
    target_file: str
    dependencies: list[str] = Field(
        default_factory=list, description="Other source files that must be migrated first"
    )
    migration_notes: str = Field(
        ..., description="Specific guidance for the Migrator agent on this file"
    )
    priority: int = Field(..., ge=1, le=10, description="1 = migrate first, 10 = migrate last")


class MigrationPlan(BaseModel):
    target_language: str
    target_architecture: ArchitectureSpec
    file_migration_order: list[FileToMigrate]
    modernization_opportunities: list[str] = Field(default_factory=list)
    estimated_effort_hours: int = Field(..., ge=1)
    risk_assessment: list[str] = Field(default_factory=list)
    architectural_rationale: str = Field(
        ..., description="Why this architecture fits the migrated codebase. Showcase reasoning."
    )


# ---------- Migrator ----------

class MigrationResult(BaseModel):
    source_file: str
    target_file: str
    migrated_code: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    semantic_notes: str = Field(
        default="", description="Anything the next agent should know about this file"
    )


# ---------- Tester ----------

class TestFile(BaseModel):
    filename: str
    code: str
    test_count: int = Field(..., ge=0)
    targets: list[str] = Field(
        default_factory=list, description="Source modules these tests cover"
    )


class TestSuite(BaseModel):
    strategy: str = Field(
        ..., description="High-level test strategy: equivalence, golden-file, property-based, etc."
    )
    test_files: list[TestFile]
    coverage_estimate: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(default="")


# ---------- Documenter ----------

class MigrationReport(BaseModel):
    title: str
    summary: str
    markdown: str = Field(..., description="Full migration report in Markdown")
