"""Verify the Pydantic schemas serialize/validate cleanly."""
from models.outputs import (
    ArchitectureSpec,
    CodebaseAnalysis,
    FileToMigrate,
    MigrationPlan,
    MigrationResult,
    ModuleInfo,
)


def test_codebase_analysis_minimal():
    a = CodebaseAnalysis(
        total_files=1,
        total_lines=100,
        modules=[
            ModuleInfo(name="ACCOUNT", file_path="ACCOUNT.cbl", lines=100, purpose="bank account")
        ],
        estimated_complexity="simple",
        domain_summary="banking",
    )
    assert a.total_files == 1
    assert a.modules[0].name == "ACCOUNT"


def test_migration_plan_round_trips():
    plan = MigrationPlan(
        target_language="python",
        target_architecture=ArchitectureSpec(
            framework="FastAPI",
            data_layer="SQLAlchemy",
        ),
        file_migration_order=[
            FileToMigrate(
                source_file="ACCOUNT.cbl",
                target_file="account.py",
                migration_notes="convert PIC clauses to Decimal",
                priority=1,
            )
        ],
        estimated_effort_hours=8,
        architectural_rationale="Because.",
    )
    blob = plan.model_dump_json()
    plan2 = MigrationPlan.model_validate_json(blob)
    assert plan2.target_architecture.framework == "FastAPI"


def test_migration_result_confidence_bounded():
    import pytest
    with pytest.raises(Exception):
        MigrationResult(
            source_file="x",
            target_file="x.py",
            migrated_code="",
            confidence=1.5,
        )
