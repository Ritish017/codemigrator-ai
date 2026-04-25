"""Smoke tests for the Nemotron client.

The live tests require NVIDIA_API_KEY to be set in the environment. They are
auto-skipped otherwise so `make test` is safe in CI without secrets.
"""
import pytest
from pydantic import BaseModel

from llm.nemotron import MODEL_MAP, NemotronClient


def test_model_map():
    assert MODEL_MAP["super"] == "nvidia/nemotron-3-super-120b-a12b"
    assert MODEL_MAP["nano"] == "nvidia/nemotron-3-nano-30b-a3b"


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
        NemotronClient()


@pytest.mark.nemotron_live
async def test_nano_smoke():
    client = NemotronClient()
    text = await client.call(
        prompt="Reply with exactly the word: pong",
        tier="nano",
        max_tokens=8,
        temperature=0.0,
    )
    assert "pong" in text.lower()


@pytest.mark.nemotron_live
async def test_super_smoke():
    client = NemotronClient()
    text = await client.call(
        prompt="Reply with exactly the word: super",
        tier="super",
        max_tokens=8,
        temperature=0.0,
    )
    assert "super" in text.lower()


@pytest.mark.nemotron_live
async def test_structured_output():
    class Reply(BaseModel):
        word: str
        length: int

    client = NemotronClient()
    parsed = await client.call(
        prompt="Return word='hello' and length=5.",
        tier="nano",
        response_model=Reply,
        max_tokens=128,
        temperature=0.0,
    )
    assert isinstance(parsed, Reply)
    assert parsed.word.lower() == "hello"


@pytest.mark.nemotron_live
async def test_metrics_track_routing():
    client = NemotronClient()
    await client.call("ping", tier="nano", max_tokens=8, temperature=0.0)
    await client.call("ping", tier="nano", max_tokens=8, temperature=0.0)
    await client.call("ping", tier="super", max_tokens=8, temperature=0.0)
    m = client.get_metrics()
    assert m["nano_calls"] == 2
    assert m["super_calls"] == 1
    assert m["nano_routing_percent"] == pytest.approx(66.7, abs=0.5)
