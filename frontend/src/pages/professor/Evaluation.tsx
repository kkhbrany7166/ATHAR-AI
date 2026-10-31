import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Callout, ErrorState, Loading, PageHeader, Section, Tag, cx } from "../../components/ui";

/* eslint-disable @typescript-eslint/no-explicit-any */
type R = any;
const SPLITS = ["dev", "heldout", "final"] as const;
const SPLIT_LABEL: Record<string, string> = { dev: "Development", heldout: "Held-out", final: "Final (untouched)" };

function Frac({ n, d, strong }: { n: number | null | undefined; d: number | null | undefined; strong?: boolean }) {
  if (n === null || n === undefined || !d) return <span className="text-faint">—</span>;
  return (
    <span className="num whitespace-nowrap">
      <span className={strong ? "text-ink font-medium" : "text-muted"}>{Math.round((n / d) * 100)}%</span>
      <span className="text-faint text-[12px] ml-1.5">{n}/{d}</span>
    </span>
  );
}

const CAPABILITIES: [string, string, string][] = [
  ["Running code and scoring tests", "Deterministic", "Sandboxed subprocess per submission"],
  ["Linking failing tests to misconceptions", "Deterministic", "Probe tags authored with the rubric"],
  ["Reading written explanations", "AI when a key is set", "Otherwise the rule reader rules-v1, always labelled"],
  ["Deciding who needs what", "Deterministic rules", "Over test results and the explanation reading"],
  ["Drafting the explanation students read", "AI when a key is set", "Otherwise a labelled template. You always edit and approve"],
  ["Proposing new follow-up checks", "AI when a key is set", "Released only if the sandbox validator accepts them"],
  ["Approving and delivering interventions", "You, then deterministic", "Approval gate, idempotent executor"],
  ["Deciding outcomes", "Deterministic", "Verifier rules verify-v1"],
  ["Classmates' follow-up attempts", "Simulated", "Demo only, through the real path, labelled"],
];

export function EvaluationPage() {
  const q = useQuery({ queryKey: ["evaluation"], queryFn: () => api<Record<string, R>>("/api/evaluation") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const data = q.data!;
  const f = data.final;
  if (!f) return <Callout title="No evaluation results yet">Run <code className="font-mono">python -m evals.run</code> in backend/.</Callout>;
  const meta = f.meta;
  const llm = meta.llm.configured;
  const readers = ["baseline", ...(llm ? ["llm"] : [])];
  const splits = SPLITS.filter((s) => data[s]);
  const ex = (s: string, r: string) => data[s]?.explanations?.[r];

  return (
    <>
      <PageHeader eyebrow="How well does ATHAR work?" title="Evaluation">
        Measured, not claimed. The final set was written and committed before anything ran on it. Every percentage shows its count.
      </PageHeader>

      {!llm && (
        <Callout tone="amber" title="No live AI results in this run">
          No model credentials were configured, so the AI reader was not measured. Its behaviour is unit-tested with mocked responses
          (negation, abstention, fabricated quotes, timeouts, malformed output), but no accuracy is claimed for it. Nothing was simulated or replayed in its place.
        </Callout>
      )}

      <Section title="Reading written explanations" aside="Correct / total">
        <div className="overflow-x-auto">
          <table className="w-full text-[14px] min-w-[640px]">
            <thead>
              <tr className="text-left text-faint text-2xs uppercase tracking-[0.1em] border-b border-line">
                <th className="font-medium py-2">Measure</th>
                {splits.map((s) => readers.map((r) => <th key={s + r} className="font-medium py-2 text-right">{SPLIT_LABEL[s]}<br />{r === "llm" ? "AI reader" : "rule reader"}</th>))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              <tr>
                <td className="py-2.5">Stopping-condition judgment (C3)</td>
                {splits.map((s) => readers.map((r) => <td key={s + r} className="py-2.5 text-right"><Frac n={ex(s, r)?.c3_correct} d={ex(s, r)?.n} strong={s === "final"} /></td>))}
              </tr>
              <tr>
                <td className="py-2.5">Misconception F1 <span className="text-faint text-[12.5px]">(tp / fp / fn)</span></td>
                {splits.map((s) => readers.map((r) => {
                  const mi = ex(s, r)?.misconceptions?.micro;
                  return <td key={s + r} className="py-2.5 text-right num">{mi ? <><span className={s === "final" ? "text-ink font-medium" : "text-muted"}>{Math.round((mi.f1 ?? 0) * 100)}%</span><span className="text-faint text-[12px] ml-1.5">{mi.tp}/{mi.fp}/{mi.fn}</span></> : "—"}</td>;
                }))}
              </tr>
              <tr className="text-faint">
                <td className="py-2.5">Trivial baseline: always “met”</td>
                {splits.map((s) => readers.map((r) => {
                  const e = ex(s, "baseline");
                  return <td key={s + r} className="py-2.5 text-right">{e ? <Frac n={Math.round(e.trivial_baseline_always_met_no_misconception.c3_accuracy * e.n)} d={e.n} /> : "—"}</td>;
                }))}
              </tr>
              <tr>
                <td className="py-2.5">Says “unclear” when evidence is thin</td>
                {splits.map((s) => readers.map((r) => <td key={s + r} className="py-2.5 text-right num text-muted">{ex(s, r)?.abstains_when_evidence_is_insufficient != null ? `${Math.round(ex(s, r).abstains_when_evidence_is_insufficient * 100)}%` : "—"}</td>))}
              </tr>
              <tr>
                <td className="py-2.5">Says “unclear” when it shouldn't</td>
                {splits.map((s) => readers.map((r) => <td key={s + r} className="py-2.5 text-right num text-muted">{ex(s, r)?.wrongly_abstains_when_decidable != null ? `${Math.round(ex(s, r).wrongly_abstains_when_decidable * 100)}%` : "—"}</td>))}
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-[13px] text-faint mt-3 max-w-prose">
          The development set is optimistic for the rule reader (its phrases were written from it). The held-out set informed the AI prompt design, so it is
          not unseen for the AI reader. The final set is unseen for every component.
        </p>
      </Section>

      {data.final2 && <Final2 f2={data.final2} />}

      <div className="grid lg:grid-cols-2 gap-x-12">
        <Section title="Final set, by kind of answer" aside="Fully correct / total">
          <table className="w-full text-[14px]">
            <tbody className="divide-y divide-line">
              {Object.entries(f.explanations.baseline.by_category as Record<string, { n: number; fully_correct: number }>).map(([cat, v]) => (
                <tr key={cat}>
                  <td className="py-2 capitalize">{cat.replaceAll("_", " ")}</td>
                  {readers.map((r) => <td key={r} className="py-2 text-right"><Frac n={f.explanations[r]?.by_category?.[cat]?.fully_correct} d={v.n} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[13px] text-faint mt-2">
            Columns: {readers.map((r) => (r === "llm" ? "AI reader" : "rule reader")).join(", ")}. Fully correct needs the exact C3 judgment too.
            {llm && <> The AI's misses on correct paraphrases and negations are “partial” instead of “met”. On negation it attributed no false misconception in {f.explanations.llm.negation.no_false_misconception}/{f.explanations.llm.negation.n} cases.</>}
          </p>
        </Section>
        <Section title="Does each student get the right help?" aside="Final set · correct action / total">
          <table className="w-full text-[14px]">
            <tbody className="divide-y divide-line">
              {["none", ...readers].map((k) => (
                <tr key={k}>
                  <td className="py-2">{k === "none" ? "Tests only (no reading)" : k === "llm" ? "Tests + AI reading" : "Tests + rule reading"}</td>
                  <td className="py-2 text-right"><Frac n={f.diagnosis?.[k]?.correct} d={f.diagnosis?.[k]?.n} strong /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[13px] text-faint mt-2">An ablation: the same diagnosis rules with and without reading the explanation.</p>
        </Section>
      </div>

      <Section title="Deterministic components" aside="Correct / total">
        <table className="w-full text-[14px]">
          <thead><tr className="text-left text-faint text-2xs uppercase tracking-[0.1em] border-b border-line"><th className="font-medium py-2">Measure</th>
            {splits.map((s) => <th key={s} className="font-medium py-2 text-right">{SPLIT_LABEL[s]}</th>)}</tr></thead>
          <tbody className="divide-y divide-line">
            <tr><td className="py-2.5">Follow-up item validator</td>{splits.map((s) => <td key={s} className="py-2.5 text-right"><Frac n={data[s].variants.correct} d={data[s].variants.n} strong={s === "final"} /></td>)}</tr>
            <tr><td className="py-2.5">Verifier outcome (rule reading)</td>{splits.map((s) => <td key={s} className="py-2.5 text-right"><Frac n={data[s].verifier.baseline.correct} d={data[s].verifier.baseline.n} strong={s === "final"} /></td>)}</tr>
            {llm && <tr><td className="py-2.5">Verifier outcome (AI reading)</td>{splits.map((s) => <td key={s} className="py-2.5 text-right"><Frac n={data[s].verifier.llm?.correct} d={data[s].verifier.llm?.n} strong={s === "final"} /></td>)}</tr>}
            <tr><td className="py-2.5">Code grading: base-case criterion</td>{splits.map((s) => <td key={s} className="py-2.5 text-right">{data[s].code ? <Frac n={Math.round(data[s].code.c2_judgment_accuracy * data[s].code.n)} d={data[s].code.n} /> : <span className="text-faint">—</span>}</td>)}</tr>
            <tr><td className="py-2.5">Misconception flag: ATHAR probes</td>{splits.map((s) => <td key={s} className="py-2.5 text-right">{data[s].code ? <Frac n={Math.round(data[s].code.stopping_condition_flag_accuracy.probes * data[s].code.n)} d={data[s].code.n} /> : <span className="text-faint">—</span>}</td>)}</tr>
            <tr className="text-faint"><td className="py-2.5">Misconception flag: “any failing test” baseline</td>{splits.map((s) => <td key={s} className="py-2.5 text-right">{data[s].code ? <Frac n={Math.round(data[s].code.stopping_condition_flag_accuracy.baseline_any_failing_test * data[s].code.n)} d={data[s].code.n} /> : "—"}</td>)}</tr>
          </tbody>
        </table>
        {data.system && <p className="text-[14px] text-muted mt-4">Workflow safety checks (approval gates, permissions, idempotent delivery, outages, malformed and fabricated output, gated generation): <span className="text-ink">{data.system.summary}</span></p>}
      </Section>

      <div className="grid lg:grid-cols-[1.2fr_1fr] gap-x-12">
        <Section title={`Final-set misses (${f.explanations.baseline.failures.length + f.verifier.baseline.failures.length + f.variants.failures.length})`} aside="Rule reader">
          <ul className="space-y-1.5 text-[13px] text-muted max-h-80 overflow-y-auto pr-2">
            {f.verifier.baseline.failures.map((x: R) => <li key={x.id}><span className="font-mono text-faint">{x.id}</span> verifier: expected {x.expected.replaceAll("_", " ")}, got {x.got.replaceAll("_", " ")}</li>)}
            {f.explanations.baseline.failures.map((x: R) => <li key={x.id}><span className="font-mono text-faint">{x.id}</span> “{x.text}” <span className="text-faint">→ {x.c3_got}</span></li>)}
          </ul>
        </Section>
        <Section title="What is AI, what is not">
          <ul className="space-y-2 text-[13.5px]">
            {CAPABILITIES.map(([what, who, how]) => (
              <li key={what} className="grid grid-cols-[1fr_auto] gap-x-3">
                <span className="text-ink">{what}<span className="block text-faint text-[12.5px]">{how}</span></span>
                <Tag tone={who.startsWith("AI") ? "amber" : who === "Simulated" ? "slate" : "neutral"}>{who}</Tag>
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <Section title="Reproduce">
        <div className={cx("grid sm:grid-cols-2 gap-x-10 gap-y-1 text-[13.5px] text-muted")}>
          <span>Commit <span className="font-mono text-ink">{meta.commit}</span> · {meta.ran_at}</span>
          <span>Reader prompt <span className="font-mono">{meta.reader_prompt_version}</span> · rules <span className="font-mono">{meta.baseline_version}</span> · verifier <span className="font-mono">{meta.verifier_version}</span></span>
          <span>LLM: {llm ? `${meta.llm.provider}:${meta.llm.model}` : "not configured"} · timeout {meta.llm.timeout_seconds}s · max {meta.llm.max_calls} calls</span>
          <span><span className="font-mono">cd backend && .venv/bin/python -m evals.run</span> → docs/EVALUATION.md</span>
          {data.spend?.length > 0 && <span>Live inference so far: {data.spend.reduce((a: number, r: R) => a + r.calls, 0)} calls, {data.spend.reduce((a: number, r: R) => a + (r.failures ?? 0), 0)} failed ·
            ≈ ${data.spend.reduce((a: number, r: R) => a + r.estimated_cost_usd, 0).toFixed(2)} estimated</span>}
        </div>
      </Section>
    </>
  );
}

function Final2({ f2 }: { f2: R }) {
  const rows = Object.entries(f2.readers as Record<string, R>).filter(([, v]) => v.n);
  const label: Record<string, string> = { rules: "Rule reader", "reader-v2": "AI reader v2", "reader-v3": "AI reader v3 (default)", "reader-v3-blind": "AI v3, explanation only (ablation)" };
  return (
    <Section title="Code and explanation together" aside="Final-2 · 24 untouched cases · correct / total">
      <div className="overflow-x-auto">
        <table className="w-full text-[14px] min-w-[640px]">
          <thead><tr className="text-left text-faint text-2xs uppercase tracking-[0.1em] border-b border-line">
            <th className="font-medium py-2">Reader</th><th className="font-medium py-2 text-right">Misconception F1</th>
            <th className="font-medium py-2 text-right">Working code, confused reasoning</th><th className="font-medium py-2 text-right">Right kind of help</th>
            <th className="font-medium py-2 text-right">C3 judgment</th></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.map(([k, v]) => (
              <tr key={k} className={k === "rules" ? "text-faint" : ""}>
                <td className="py-2.5">{label[k] ?? k}</td>
                <td className="py-2.5 text-right num">{Math.round(v.misconceptions.micro.f1 * 100)}%<span className="text-faint text-[12px] ml-1.5">{v.misconceptions.micro.tp}/{v.misconceptions.micro.fp}/{v.misconceptions.micro.fn}</span></td>
                <td className="py-2.5 text-right"><Frac n={v.working_code_confused_reasoning.caught} d={v.working_code_confused_reasoning.n} strong={k !== "rules"} /></td>
                <td className="py-2.5 text-right"><Frac n={v.category_correct} d={v.n} /></td>
                <td className="py-2.5 text-right"><Frac n={v.c3_correct} d={v.n} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[13px] text-faint mt-3 max-w-prose">
        The AI reader catches confused reasoning behind working code that rules miss. Its main weakness is calibration: it calls most correct
        explanations “partial”, so ATHAR under-certifies understanding and sends those students a short explain-your-reasoning task instead.
        That errs on the side of caution, not harm. The explanation-only ablation was prompted partly by one case in this set, so it is
        reported as an ablation, not as a clean result.
      </p>
    </Section>
  );
}
