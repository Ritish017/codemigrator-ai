"""
NVIDIA Nemotron 3 client for CodeMigrator AI.

Wraps the NIM OpenAI-compatible endpoint with our tier abstraction.
This is the ONLY LLM module in the codebase. No other providers.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import AsyncIterator, Literal, TypeVar

from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T", bound=BaseModel)

NemotronTier = Literal["super", "nano"]

MODEL_MAP: dict[NemotronTier, str] = {
    "super": "nvidia/nemotron-3-super-120b-a12b",
    "nano": "nvidia/nemotron-3-nano-30b-a3b",
}

# NVIDIA has not published per-token pricing for these specific NIM-hosted models,
# so we report token usage only and leave cost surfaced separately if/when verified.
# The free tier is free; treat any cost you see as "tokens used", not dollars.
COST_PER_1K: dict[NemotronTier, float] = {
    "super": 0.0,
    "nano": 0.0,
}

# Stay safely below the 40 req/min free-tier ceiling.
_request_semaphore = asyncio.Semaphore(15)


class NemotronCallError(RuntimeError):
    """Wraps a Nemotron API failure with context."""


class NemotronClient:
    """NVIDIA Nemotron client using NIM API.

    Tier semantics:
        - "super" -> nvidia/nemotron-3-super-120b-a12b (deep reasoning, 1M ctx)
        - "nano"  -> nvidia/nemotron-3-nano-30b-a3b (high-throughput conversion)
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "NVIDIA_API_KEY not set. Get a free key at https://build.nvidia.com"
            )
        if not self.api_key.startswith("nvapi-"):
            logger.warning("API key should start with 'nvapi-' — verify you copied a NIM key")

        self.base_url = base_url or os.environ.get(
            "NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

        # Telemetry surfaced to the UI metrics card.
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self.calls_per_tier: dict[NemotronTier, int] = {"super": 0, "nano": 0}
        self.tokens_per_tier: dict[NemotronTier, int] = {"super": 0, "nano": 0}
        self.latency_per_tier: dict[NemotronTier, list[float]] = {"super": [], "nano": []}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((NemotronCallError, TimeoutError)),
        reraise=True,
    )
    async def call(
        self,
        prompt: str,
        tier: NemotronTier,
        system: str | None = None,
        response_model: type[T] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.6,
        top_p: float = 0.95,
    ) -> str | T:
        """Call Nemotron with optional structured Pydantic output.

        When `response_model` is provided we append the JSON schema to the prompt
        and parse the response into the model. This keeps things simple while the
        NIM endpoint matures its native structured-output support.
        """
        async with _request_semaphore:
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})

            user_prompt = prompt
            if response_model is not None:
                schema = response_model.model_json_schema()
                user_prompt = (
                    f"{prompt}\n\n"
                    "Respond with ONLY valid JSON matching this schema. "
                    "No markdown fences, no preamble, no commentary.\n\n"
                    f"```schema\n{json.dumps(schema, indent=2)}\n```"
                )
            messages.append({"role": "user", "content": user_prompt})

            logger.info(
                "nemotron.call tier={} model={} prompt_chars={} structured={}",
                tier,
                MODEL_MAP[tier],
                len(user_prompt),
                response_model.__name__ if response_model else "no",
            )

            t0 = time.perf_counter()
            try:
                response = await self.client.chat.completions.create(
                    model=MODEL_MAP[tier],
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
            except Exception as exc:  # noqa: BLE001 - re-raise as our own type for tenacity
                raise NemotronCallError(f"NIM call failed (tier={tier}): {exc}") from exc

            latency = time.perf_counter() - t0

            text = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            # Update telemetry.
            self.total_tokens += tokens
            self.tokens_per_tier[tier] += tokens
            self.calls_per_tier[tier] += 1
            self.latency_per_tier[tier].append(latency)
            self.total_cost += (tokens / 1000.0) * COST_PER_1K[tier]

            logger.success(
                "nemotron.done tier={} tokens={} latency={:.2f}s",
                tier,
                tokens,
                latency,
            )

            if response_model is not None:
                return self._parse_structured(text, response_model)
            return text

    @staticmethod
    def _parse_structured(text: str, response_model: type[T]) -> T:
        """Strip markdown fences if present, then validate."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove leading fence (optionally with language tag).
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        # Some models prepend a {"json": ...} wrapper; try to find first { or [.
        for opener in ("{", "["):
            idx = cleaned.find(opener)
            if idx > 0:
                cleaned = cleaned[idx:]
                break
        try:
            return response_model.model_validate_json(cleaned)
        except Exception as exc:
            logger.error("Failed to parse structured output: {}", cleaned[:500])
            raise NemotronCallError(
                f"Could not parse {response_model.__name__} from Nemotron output"
            ) from exc

    async def stream(
        self,
        prompt: str,
        tier: NemotronTier,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.6,
    ) -> AsyncIterator[str]:
        """Stream tokens from Nemotron — used by the architect for the live thinking pane."""
        async with _request_semaphore:
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            stream = await self.client.chat.completions.create(
                model=MODEL_MAP[tier],
                messages=messages,
                stream=True,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
            )

            self.calls_per_tier[tier] += 1
            chunks_received = 0
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    chunks_received += 1
                    yield delta
            logger.info("nemotron.stream tier={} chunks={}", tier, chunks_received)

    def get_metrics(self) -> dict:
        """Snapshot for the UI metrics card."""
        total_calls = sum(self.calls_per_tier.values())
        nano_pct = (
            self.calls_per_tier["nano"] / total_calls * 100.0 if total_calls > 0 else 0.0
        )

        def _avg(xs: list[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "super_calls": self.calls_per_tier["super"],
            "nano_calls": self.calls_per_tier["nano"],
            "super_tokens": self.tokens_per_tier["super"],
            "nano_tokens": self.tokens_per_tier["nano"],
            "nano_routing_percent": round(nano_pct, 1),
            "avg_latency_super_s": round(_avg(self.latency_per_tier["super"]), 2),
            "avg_latency_nano_s": round(_avg(self.latency_per_tier["nano"]), 2),
        }

    def reset_metrics(self) -> None:
        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls_per_tier = {"super": 0, "nano": 0}
        self.tokens_per_tier = {"super": 0, "nano": 0}
        self.latency_per_tier = {"super": [], "nano": []}


_singleton: NemotronClient | None = None


def get_client() -> NemotronClient:
    """Lazy singleton so tests can monkeypatch the env before construction."""
    global _singleton
    if _singleton is None:
        _singleton = NemotronClient()
    return _singleton
