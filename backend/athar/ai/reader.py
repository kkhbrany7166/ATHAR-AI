"""Choose how written explanations are read: an LLM, the rule baseline, or not at all.

ATHAR_ANALYZER=auto  → the LLM if one is configured, otherwise the rule baseline (labelled as such)
ATHAR_ANALYZER=llm   → the LLM only; without one, explanations are marked "not analysed"
ATHAR_ANALYZER=baseline / none
A fourth kind, "replay", is only chosen explicitly (`athar.cli reset --replay`): recorded readings of the demo class.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import get_settings
from . import baseline, explanations
from .explanations import ValidatedAnalysis
from .provider import LLMProvider, get_provider
from .replay import Recording


@dataclass
class Reader:
    kind: str  # llm | baseline | replay | none
    provider: LLMProvider | None = None
    recording: "Recording | None" = None

    @property
    def source(self) -> str:
        return {"llm": "ai", "baseline": "baseline", "replay": "ai"}.get(self.kind, "ai")

    @property
    def label(self) -> str:
        if self.kind == "llm":
            return f"{self.provider.name}:{self.provider.model}"
        if self.kind == "replay":
            return self.recording.label
        return baseline.VERSION if self.kind == "baseline" else "none"

    def read(self, *, explanation: str, criteria: list[dict], misconceptions: list[dict], **ctx: str) -> ValidatedAnalysis:
        student = ctx.pop("student", "")  # used only to look up a recording; never sent to a model
        if self.kind == "llm":
            return explanations.analyze(self.provider, explanation=explanation, criteria=criteria, misconceptions=misconceptions, **ctx)
        if self.kind == "baseline":
            return baseline.analyze(explanation, criteria)
        if self.kind == "replay":
            return self.recording.analysis(student, ctx.get("code", ""), explanation)
        raise RuntimeError("no reader configured")


_mode_override: str | None = None


def set_analyzer_override(mode: str | None) -> None:
    global _mode_override
    _mode_override = mode


def choose_reader() -> Reader:
    mode = _mode_override or get_settings().analyzer
    provider = get_provider() if mode in ("auto", "llm") else None
    if provider is not None:
        return Reader("llm", provider)
    if mode in ("auto", "baseline"):
        return Reader("baseline")
    return Reader("none")


def replay_reader() -> Reader:
    return Reader("replay", recording=Recording())
