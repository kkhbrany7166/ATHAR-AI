import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Callout, ErrorState, Loading, PageHeader, Section } from "../../components/ui";

/* eslint-disable @typescript-eslint/no-explicit-any */
type R = any;

const pct = (x: number | null | undefined) => (x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`);

export function EvaluationPage() {
  const q = useQuery({ queryKey: ["evaluation"], queryFn: () => api<{ dev: R; heldout: R; system: R }>("/api/evaluation") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const { dev, heldout: h, system } = q.data!;
  if (!h) return <Callout title="No evaluation results yet">Run <code className="font-mono">python -m evals.run</code> in backend/.</Callout>;
  const llm = h.meta.llm.configured;

  const rows: [string, string, number | null, number | null, string?][] = [
    ["Code grading", "Base-case criterion judged correctly", dev?.code.c2_judgment_accuracy, h.code.c2_judgment_accuracy],
    ["Code grading", "Misconception set matches the instructor's label", dev?.code.exact_set_accuracy, h.code.exact_set_accuracy],
    ["Code grading", "Stopping-condition flag: ATHAR probe tests", dev?.code.stopping_condition_flag_accuracy.probes, h.code.stopping_condition_flag_accuracy.probes],
    ["Code grading", "Stopping-condition flag: baseline (any failing test)", dev?.code.stopping_condition_flag_accuracy.baseline_any_failing_test, h.code.stopping_condition_flag_accuracy.baseline_any_failing_test, "baseline"],
    ["Explanation reading", "Misconception micro-F1: rule reader", dev?.explanations.baseline.misconceptions.micro.f1, h.explanations.baseline.misconceptions.micro.f1],
    ["Explanation reading", "Stopping-condition judgment: rule reader", dev?.explanations.baseline.c3_accuracy, h.explanations.baseline.c3_accuracy],
    ["Explanation reading", "Stopping-condition judgment: always 'met'", dev?.explanations.baseline.trivial_baseline_always_met_no_misconception.c3_accuracy, h.explanations.baseline.trivial_baseline_always_met_no_misconception.c3_accuracy, "baseline"],
    ["Verification", "Outcome matches the instructor's call", dev?.verifier.baseline.accuracy, h.verifier.baseline.accuracy],
    ["Validation", "Follow-up items accepted/rejected correctly", dev?.variants.accuracy, h.variants.accuracy],
  ];
  if (llm) {
    rows.splice(6, 0,
      ["Explanation reading", "Misconception micro-F1: LLM reader", dev?.explanations.llm.misconceptions?.micro.f1, h.explanations.llm.misconceptions?.micro.f1],
      ["Explanation reading", "Stopping-condition judgment: LLM reader", dev?.explanations.llm.c3_accuracy, h.explanations.llm.c3_accuracy]);
  }

  return (
    <>
      <PageHeader eyebrow="How well does ATHAR work?" title="Evaluation">
        Measured on hand-written held-out cases that no component was tuned on, next to the development set and simple baselines.
        Run {h.meta.ran_at} at commit <span className="font-mono text-[13px]">{h.meta.commit}</span>.
      </PageHeader>
      {!llm && (
        <Callout tone="amber" title="No LLM results in this run">
          No model credentials were configured, so only deterministic components and the rule-based reader were measured.
          Nothing was simulated or replayed in their place. The same cases run through the LLM reader automatically once a key is set.
        </Callout>
      )}
      <Section title="Results" aside={`Held-out: ${h.code.n} programs · ${h.explanations.baseline.n} explanations · ${h.verifier.baseline.n} attempts · ${h.variants.n} items`}>
        <table className="w-full text-[14px]">
          <thead>
            <tr className="text-left text-faint text-2xs uppercase tracking-[0.1em] border-b border-line">
              <th className="font-medium py-2 w-[150px]">Suite</th><th className="font-medium py-2">Measure</th>
              <th className="font-medium py-2 text-right w-[90px]">Dev</th><th className="font-medium py-2 text-right w-[110px]">Held-out</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map(([suite, label, d, v, kind]) => (
              <tr key={label} className={kind === "baseline" ? "text-faint" : ""}>
                <td className="py-2.5 text-muted">{suite}</td>
                <td className="py-2.5">{label}</td>
                <td className="py-2.5 text-right num text-muted">{pct(d)}</td>
                <td className="py-2.5 text-right num font-medium">{pct(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {system && <p className="text-[13.5px] text-muted mt-4">System checks (approval gates, permissions, idempotent delivery, persistence, outage handling): <span className="text-ink">{system.summary}</span></p>}
      </Section>
      <div className="grid md:grid-cols-2 gap-x-12">
        <Section title="What this shows">
          <ul className="space-y-2.5 text-[14px] text-muted list-disc ml-4">
            <li>Deterministic parts (sandboxed tests, probes, the validator) hold up on unseen code styles.</li>
            <li>The rule-based reader falls apart on unfamiliar phrasing. That gap is why reading explanations is the job the LLM is meant to do, and why every reading needs your confirmation.</li>
            <li>The verifier only says <em>demonstrated</em> when tests and reasoning agree, so its mistakes lean cautious.</li>
          </ul>
        </Section>
        <Section title={`Held-out misses (${h.code.failures.length + h.explanations.baseline.failures.length + h.verifier.baseline.failures.length + h.variants.failures.length})`}>
          <ul className="space-y-1.5 text-[13px] text-muted max-h-72 overflow-y-auto pr-2">
            {h.verifier.baseline.failures.map((f: R) => <li key={f.id}><span className="font-mono text-faint">{f.id}</span> verifier: expected {f.expected}, got {f.got}</li>)}
            {h.code.failures.map((f: R) => <li key={f.id}><span className="font-mono text-faint">{f.id}</span> grading: expected {f.expected.join(", ") || "none"}, found {f.found.join(", ") || "none"}</li>)}
            {h.explanations.baseline.failures.map((f: R) => <li key={f.id}><span className="font-mono text-faint">{f.id}</span> “{f.text}”</li>)}
          </ul>
          <p className="text-[12.5px] text-faint mt-3">Full case-by-case report: docs/EVALUATION.md</p>
        </Section>
      </div>
    </>
  );
}
