"""LLM provider abstraction.

ATHAR uses LLMs for focused judgments that return validated, structured data. Callers get
either a parsed Pydantic object or an exception. There is no silent fallback: when no provider is
configured, `get_provider()` returns None and callers record the work as `ai_unavailable`.
"""

from __future__ import annotations

import os
import threading
from typing import Protocol, TypeVar

from pydantic import BaseModel

from ..config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """The provider did not return usable output (timeout, refusal, truncation, malformed/invalid schema, API error, budget)."""


TIMEOUT_SECONDS = float(os.getenv("ATHAR_LLM_TIMEOUT", "45"))
MAX_CALLS = int(os.getenv("ATHAR_LLM_MAX_CALLS", "400"))  # per process: a hard ceiling on spend


class _Budget:
    def __init__(self, limit: int):
        self.limit, self.used, self._lock = limit, 0, threading.Lock()

    def take(self) -> None:
        with self._lock:
            if self.used >= self.limit:
                raise LLMError(f"LLM call budget exhausted ({self.limit} calls); raise ATHAR_LLM_MAX_CALLS deliberately if needed")
            self.used += 1


BUDGET = _Budget(MAX_CALLS)


class LLMProvider(Protocol):
    name: str
    model: str

    def parse(self, system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T: ...

    def chat(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(max_retries=1, timeout=TIMEOUT_SECONDS)
        self.model = model

    def parse(self, system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T:
        BUDGET.take()
        try:
            resp = self.client.messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
        except self._anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e.__class__.__name__}: {e}") from e
        except Exception as e:  # malformed JSON / schema validation inside the SDK's parser
            raise LLMError(f"malformed model output: {e.__class__.__name__}") from e
        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request")
        if resp.stop_reason == "max_tokens":
            raise LLMError("output truncated at max_tokens")
        if resp.parsed_output is None:
            raise LLMError("no structured output returned")
        return resp.parsed_output

    def chat(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str:
        BUDGET.take()
        try:
            resp = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system, messages=messages)
        except self._anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e.__class__.__name__}: {e}") from e
        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request")
        return "".join(b.text for b in resp.content if b.type == "text")


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str):
        import openai

        self._openai = openai
        self.client = openai.OpenAI(max_retries=1, timeout=TIMEOUT_SECONDS)
        self.model = model

    def parse(self, system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T:
        BUDGET.take()
        try:
            resp = self.client.chat.completions.parse(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format=schema,
                max_completion_tokens=max_tokens,
            )
        except self._openai.OpenAIError as e:
            raise LLMError(f"OpenAI API error: {e.__class__.__name__}: {e}") from e
        except Exception as e:  # malformed JSON / schema validation inside the SDK's parser
            raise LLMError(f"malformed model output: {e.__class__.__name__}") from e
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise LLMError("model declined the request")
        if msg.parsed is None:
            raise LLMError("no structured output returned")
        return msg.parsed

    def chat(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str:
        BUDGET.take()
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, *messages],
                max_completion_tokens=max_tokens,
            )
        except self._openai.OpenAIError as e:
            raise LLMError(f"OpenAI API error: {e.__class__.__name__}: {e}") from e
        return resp.choices[0].message.content or ""


_override: LLMProvider | None = None
_override_set = False


def set_provider_override(provider: LLMProvider | None) -> None:
    """Tests use this to inject a scripted provider (or force 'unavailable')."""
    global _override, _override_set
    _override, _override_set = provider, True


def clear_provider_override() -> None:
    global _override, _override_set
    _override, _override_set = None, False


def get_provider() -> LLMProvider | None:
    if _override_set:
        return _override
    s = get_settings()
    if s.llm_provider == "anthropic":
        return AnthropicProvider(s.anthropic_model)
    if s.llm_provider == "openai":
        return OpenAIProvider(s.openai_model)
    return None


def provider_status() -> dict[str, object]:
    s = get_settings()
    p = s.llm_provider
    model = s.anthropic_model if p == "anthropic" else s.openai_model if p == "openai" else ""
    if _override_set:
        return {"provider": _override.name if _override else "none", "model": _override.model if _override else "",
                "configured": _override is not None}
    return {"provider": p, "model": model, "configured": p in ("anthropic", "openai"), "analyzer": s.analyzer,
            "timeout_seconds": TIMEOUT_SECONDS, "max_calls": MAX_CALLS}
