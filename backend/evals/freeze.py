"""Record exactly what is being evaluated, before a run: model config, prompt hash, dataset hashes, scoring rules.

    .venv/bin/python -m evals.freeze   →  writes evals/FREEZE.json (commit it before running the evaluation)
"""

from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import time
from pathlib import Path

from athar.ai import baseline, explanations
from athar.ai.provider import provider_status
from athar.interventions import planning, verifier

ROOT = Path(__file__).resolve().parent


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def main() -> None:
    datasets = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / "datasets").rglob("*.json"))}
    prompt_src = explanations.SYSTEM + inspect.getsource(explanations.build_prompt) + json.dumps(explanations.ExplanationReading.model_json_schema(), sort_keys=True)
    freeze = {
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "llm": {k: v for k, v in provider_status().items()},
        "sampling": "provider defaults (temperature not set); structured output via chat.completions.parse",
        "reader_prompt_version": explanations.PROMPT_VERSION, "reader_prompt_sha": sha(prompt_src.encode()),
        "validation_sha": sha(inspect.getsource(explanations.validate).encode()),
        "rule_baseline": baseline.VERSION, "rule_baseline_sha": sha(inspect.getsource(baseline).encode()),
        "verifier": verifier.RULE_VERSION, "verifier_sha": sha(inspect.getsource(verifier).encode()),
        "planning_sha": sha(inspect.getsource(planning).encode()),
        "datasets": datasets,
        "scoring": {
            "explanations": "Per case: held misconceptions (MC-STOP-IMPLICIT, MC-BASE-SMALLEST) vs label → micro P/R/F1; C3 judgment exact match "
                            "(met / not_met / unclear; partial counts as wrong). 'Rejects' findings are not held. Errors count as wrong with no misconception.",
            "verifier": "Outcome exact match (demonstrated / still_developing / insufficient_evidence) from sandbox tests + reading + verify-v1 rules.",
            "diagnosis": "Category exact match from sandbox + probes + reading + planning rules.",
            "variants": "Validator valid/invalid vs label.",
        },
    }
    out = ROOT / "FREEZE.json"
    out.write_text(json.dumps(freeze, indent=2))
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
