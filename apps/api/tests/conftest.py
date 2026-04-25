"""Shared test fixtures."""
import os
import sys
from pathlib import Path

# Ensure apps/api is on sys.path so `import llm` etc. work in tests.
HERE = Path(__file__).resolve().parent
API_ROOT = HERE.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def pytest_collection_modifyitems(config, items):
    """Skip Nemotron-calling tests if no API key is set."""
    if os.environ.get("NVIDIA_API_KEY"):
        return
    import pytest
    skip = pytest.mark.skip(reason="NVIDIA_API_KEY not set; skipping live Nemotron tests")
    for item in items:
        if "nemotron_live" in item.keywords:
            item.add_marker(skip)
