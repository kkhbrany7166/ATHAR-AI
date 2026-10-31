"""Run untrusted Python submissions against test cases in a separate, resource-limited process.

This is a prototype-grade sandbox: a fresh interpreter in isolated mode (-I), an empty temp
working directory, CPU / memory / file-size / process limits, a per-test alarm and a wall-clock
timeout. It does NOT block network or filesystem reads. Production use needs a container or
gVisor/nsjail runner behind the same `run_tests` interface.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The harness runs inside the child process. It execs the submission, then calls each test.
_HARNESS = r'''
import json, signal, sys
sys.setrecursionlimit(400)
spec = json.loads(sys.stdin.read())

class _Timeout(Exception):
    pass

def _alarm(signum, frame):
    raise _Timeout()

signal.signal(signal.SIGALRM, _alarm)
out = {"load_error": None, "results": []}
ns = {"__name__": "submission"}
try:
    exec(compile(spec["code"], "submission.py", "exec"), ns)
except BaseException as e:  # syntax errors, top-level crashes
    out["load_error"] = {"type": type(e).__name__, "message": str(e)[:300]}
    print("@@ATHAR@@" + json.dumps(out))
    sys.exit(0)

for t in spec["tests"]:
    r = {"id": t["id"], "status": "pass", "actual": "", "error_type": "", "error_message": ""}
    fn = ns.get(t["function"])
    if not callable(fn):
        r.update(status="error", error_type="NameError", error_message=f"function {t['function']!r} is not defined")
        out["results"].append(r)
        continue
    signal.setitimer(signal.ITIMER_REAL, spec["per_test_seconds"])
    try:
        actual = fn(*t["args"])
        signal.setitimer(signal.ITIMER_REAL, 0)
        r["actual"] = repr(actual)[:200]
        if actual != t["expected"]:
            r["status"] = "fail"
    except _Timeout:
        r.update(status="timeout", error_type="Timeout", error_message="test exceeded time limit")
    except BaseException as e:
        signal.setitimer(signal.ITIMER_REAL, 0)
        r.update(status="error", error_type=type(e).__name__, error_message=str(e)[:300])
    out["results"].append(r)

print("@@ATHAR@@" + json.dumps(out))
'''


@dataclass(frozen=True)
class TestSpec:
    __test__ = False
    id: int
    function: str
    args: list[Any]
    expected: Any


@dataclass
class TestOutcome:
    __test__ = False
    id: int
    status: str  # pass | fail | error | timeout | not_run
    actual: str = ""
    error_type: str = ""
    error_message: str = ""


@dataclass
class RunReport:
    outcomes: list[TestOutcome]
    load_error: dict[str, str] | None = None
    infrastructure_error: str | None = None


def _limit_resources() -> None:  # runs in the child before exec
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except (ValueError, OSError):
        pass
    try:  # not enforced on macOS, effective on Linux
        resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    except (ValueError, OSError):
        pass


def run_tests(code: str, tests: list[TestSpec], per_test_seconds: float = 1.0, wall_seconds: float = 10.0) -> RunReport:
    spec = {
        "code": code,
        "per_test_seconds": per_test_seconds,
        "tests": [{"id": t.id, "function": t.function, "args": t.args, "expected": t.expected} for t in tests],
    }
    with tempfile.TemporaryDirectory(prefix="athar-run-") as tmp:
        harness = Path(tmp) / "harness.py"
        harness.write_text(_HARNESS)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(harness)],
                input=json.dumps(spec),
                capture_output=True,
                text=True,
                cwd=tmp,
                timeout=wall_seconds,
                preexec_fn=_limit_resources,
                env={"PYTHONHASHSEED": "0"},
            )
        except subprocess.TimeoutExpired:
            return RunReport(
                outcomes=[TestOutcome(t.id, "timeout", error_type="Timeout", error_message="submission exceeded wall-clock limit") for t in tests]
            )

    marker = next((line for line in reversed(proc.stdout.splitlines()) if line.startswith("@@ATHAR@@")), None)
    if marker is None:
        # The child died without reporting (e.g. killed by CPU limit). Every test is unresolved.
        reason = (proc.stderr or "").strip().splitlines()[-1:] or [f"exit code {proc.returncode}"]
        return RunReport(
            outcomes=[TestOutcome(t.id, "error", error_type="Crash", error_message=reason[0][:300]) for t in tests],
            infrastructure_error=None,
        )
    data = json.loads(marker.removeprefix("@@ATHAR@@"))
    if data["load_error"]:
        le = data["load_error"]
        return RunReport(
            outcomes=[TestOutcome(t.id, "error", error_type=le["type"], error_message=le["message"]) for t in tests],
            load_error=le,
        )
    return RunReport(outcomes=[TestOutcome(**r) for r in data["results"]])
