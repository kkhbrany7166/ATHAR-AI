from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from athar import db as dbmod
from athar.ai.explanations import CriterionJudgment, ExplanationAnalysis, MisconceptionSignal
from athar.ai.provider import LLMError, clear_provider_override, set_provider_override
from athar.ai.reader import set_analyzer_override
from athar.seed.demo import seed_demo


@pytest.fixture(autouse=True)
def _never_call_live_models(monkeypatch):
    """Tests must never spend money or depend on the network, even when backend/.env holds a real key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    set_provider_override(None)
    yield
    clear_provider_override()
    set_analyzer_override(None)


@pytest.fixture()
def world(tmp_path):
    dbmod.configure(f"sqlite:///{tmp_path / 'test.db'}")
    dbmod.reset_db()
    with dbmod.SessionLocal() as s:
        ids = seed_demo(s)
    yield ids
    clear_provider_override()
    set_analyzer_override(None)


@pytest.fixture()
def db(world):
    with dbmod.SessionLocal() as s:
        yield s


@pytest.fixture()
def client(world):
    from athar.main import create_app

    with TestClient(create_app()) as c:
        yield c


def login(client: TestClient, user_id: int) -> dict[str, str]:
    token = client.post("/api/auth/demo-login", json={"user_id": user_id}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------------------------
# Test doubles for the LLM. These exist only in tests; production never uses scripted output.
# ---------------------------------------------------------------------------------------------

IMPLICIT_MARKERS = ["stops on its own", "return statement", "return line", "nothing left to multiply", "small enough",
                    "reaches the end"]


def _explanation(user_prompt: str) -> str:
    return re.search(r"<student_explanation>\n(.*)\n</student_explanation>", user_prompt, re.S).group(1)


class ScriptedProvider:
    """Reads the explanation and returns a plausible, *verbatim-quoted* analysis."""

    name, model = "scripted", "test-double"

    def __init__(self, fabricate_quotes: bool = False):
        self.fabricate_quotes = fabricate_quotes
        self.calls = 0

    def parse(self, system, user, schema, max_tokens=4000):
        self.calls += 1
        text = _explanation(user)
        first = text.split(".")[0]
        signals = []
        for marker in IMPLICIT_MARKERS:
            if marker in text.lower():
                start = text.lower().index(marker)
                quote = text[start:start + len(marker)]
                signals.append(MisconceptionSignal(code="MC-STOP-IMPLICIT", quote=quote if not self.fabricate_quotes else "recursion is magic",
                                                   reasoning="attributes stopping to something other than a condition", confidence="high"))
                break
        judgment = "not_met" if signals else "met"
        return ExplanationAnalysis(
            criteria=[CriterionJudgment(criterion_code="C3", judgment=judgment, rationale="scripted", quotes=[first], confidence="high"),
                      CriterionJudgment(criterion_code="C4", judgment="met", rationale="scripted", quotes=[first], confidence="medium")],
            misconceptions=signals,
        )

    def chat(self, system, messages, max_tokens=2000):
        return "scripted"


class FailingProvider:
    name, model = "failing", "test-double"

    def parse(self, *a, **k):
        raise LLMError("simulated outage")

    def chat(self, *a, **k):
        raise LLMError("simulated outage")


@pytest.fixture()
def scripted():
    p = ScriptedProvider()
    set_provider_override(p)
    return p


@pytest.fixture()
def no_llm():
    """No LLM and no rule baseline: explanations stay unanalysed."""
    set_provider_override(None)
    set_analyzer_override("none")


@pytest.fixture()
def rule_baseline():
    set_provider_override(None)
    set_analyzer_override("baseline")
