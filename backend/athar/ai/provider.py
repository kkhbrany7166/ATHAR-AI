"""LLM provider abstraction.

ATHAR uses LLMs for focused judgments that return validated, structured data. Callers get
either a parsed Pydantic object or an exception. There is no silent fallback: when no provider is
configured, `get_provider()` returns None and callers record the work as `ai_unavailable`.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from ..config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """The provider was reachable but did not return usable output (refusal, truncation, invalid schema, API error)."""


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
        self.client = anthropic.Anthropic(max_retries=2, timeout=120.0)
        self.model = model

    def parse(self, system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T:
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
        if resp.stop_reason == "refusal":
            raise LLMError("model declined the request")
        if resp.stop_reason == "max_tokens":
            raise LLMError("output truncated at max_tokens")
        if resp.parsed_output is None:
            raise LLMError("no structured output returned")
        return resp.parsed_output

    def chat(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str:
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
        self.client = openai.OpenAI(max_retries=2, timeout=120.0)
        self.model = model

    def parse(self, system: str, user: str, schema: type[T], max_tokens: int = 4000) -> T:
        try:
            resp = self.client.chat.completions.parse(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format=schema,
                max_completion_tokens=max_tokens,
            )
        except self._openai.OpenAIError as e:
            raise LLMError(f"OpenAI API error: {e.__class__.__name__}: {e}") from e
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise LLMError("model declined the request")
        if msg.parsed is None:
            raise LLMError("no structured output returned")
        return msg.parsed

    def chat(self, system: str, messages: list[dict[str, str]], max_tokens: int = 2000) -> str:
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
    return {"provider": p, "model": model, "configured": p in ("anthropic", "openai")}
