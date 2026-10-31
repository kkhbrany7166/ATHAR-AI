// Submission review: "What does this student's work show, and what do I decide?"
// Order on the page: the finding in one sentence → the student's own work → supporting evidence → your decision.
// Everything else (full AI reading, every test, rationales) is one click away, never removed.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { criterionLabel, misconceptionLabel, objectiveLabel } from "../../lib/labels";
import type { Evidence, SubmissionDetail } from "../../lib/types";
import { EvidenceTag, sourceKind } from "../../components/Evidence";
import { Button, CONDITIONS, Callout, CodeBlock, ErrorState, Highlighted, JudgmentMark, Loading, SynthTag, Tag, cx } from "../../components/ui";

type Detail = SubmissionDetail;
const MACHINE = ["ai", "baseline"];

/** Deterministic one-line findings built from stored evidence. No new model output. */
function findings(d: Detail) {
  const passed = d.tests.filter((t) => t.status === "pass").length;
  const failing = d.tests.filter((t) => t.status !== "pass");
  const loadFailed = failing.length === d.tests.length && d.tests.length > 0 && ["SyntaxError", "NameError", "Crash"].includes(failing[0]?.error_type);
  const testCodes = [...new Set(d.misconceptions.filter((m) => m.source === "tests").map((m) => m.code))];
  const heldCodes = [...new Set(d.misconceptions.filter((m) => MACHINE.includes(m.source)).map((m) => m.code))];
  const stopJudgment = d.criteria.find((c) => c.code === "C3")?.state.judgment;
  const ai = d.reading?.source === "ai";
  const who = ai ? "AI" : "rule";

  const code = loadFailed
    ? `The code didn't run (${failing[0].error_type}), so the tests can't show anything about recursion.`
    : failing.length === 0
      ? `The code passes all ${d.tests.length} tests.`
      : `The code passes ${passed} of ${d.tests.length} tests. It fails ${failing.slice(0, 2).map((t) => `${t.name.split(" is ")[0]} (${t.error_type || "wrong value"})`).join(" and ")}${failing.length > 2 ? ` and ${failing.length - 2} more` : ""}.`;

  let reasoning: string;
  if (!d.explanation.trim()) reasoning = "There is no written explanation.";
  else if (d.reading?.abstained) reasoning = `The ${who} reader didn't judge the explanation: ${d.reading.abstain_reason || "too little to go on"}.`;
  else if (heldCodes.length) reasoning = `The ${who} reading suggests the explanation holds a different idea: ${heldCodes.map((c) => misconceptionLabel(c).toLowerCase()).join("; ")}.`;
  else if (stopJudgment === "met") reasoning = `The ${who} reading found a correct stopping condition in the explanation.`;
  else if (stopJudgment === "ai_unavailable") reasoning = "The explanation hasn't been read yet.";
  else reasoning = `The ${who} reading couldn't confirm the explanation (${(stopJudgment ?? "no judgment").replace("_", " ")}).`;

  let conflict: string | null = null;
  if (testCodes.length && stopJudgment === "met" && !heldCodes.length) conflict = "The explanation describes a correct stopping condition, but the code doesn't implement it. Worth a conversation, not a penalty for the reasoning.";
  else if (failing.length === 0 && heldCodes.length) conflict = "The code works, but the explanation suggests a different belief about why it stops. This is the case tests alone can't see.";
  else if (loadFailed && stopJudgment === "met") conflict = "The reasoning reads as correct; the failure is a code error unrelated to recursion.";
  return { code, reasoning, conflict, testCodes, ai, failing };
}

export function SubmissionPage() {
  const { submissionId } = useParams();
  const qc = useQueryClient();
  const key = ["submission", submissionId];
  const q = useQuery({ queryKey: key, queryFn: () => api<Detail>(`/api/professor/submissions/${submissionId}`) });
  const refresh = (d: Detail) => {
    qc.setQueryData(key, d);
    qc.invalidateQueries({ queryKey: ["submissions", String(d.assignment_id)] });
    qc.invalidateQueries({ queryKey: ["assignment", String(d.assignment_id)] });
  };
  const [showAllTests, setShowAllTests] = useState(false);

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const d = q.data!;
  const f = findings(d);
  const quotes = [...d.criteria.flatMap((c) => c.evidence.flatMap((e) => e.quotes)), ...d.misconceptions.map((m) => m.quote).filter(Boolean)];
  let listHref = `/p/assignments/${d.assignment_id}?tab=submissions`;
  try { listHref = sessionStorage.getItem("athar.submissionsList") || listHref; } catch { /* storage unavailable */ }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 text-[14px]">
        <Link to={listHref} className="text-muted hover:text-ink">← Back to all submissions</Link>
        <span className="text-faint">{d.assignment_title.split("—")[0].trim()}</span>
      </div>

      <header className="flex flex-wrap items-end justify-between gap-4 pb-6 border-b border-line">
        <div>
          <h1 className="font-serif text-[34px] leading-tight">{d.student.name}</h1>
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            {d.is_synthetic && <SynthTag />}
            <Tag title={CONDITIONS[d.conditions]?.help}>{CONDITIONS[d.conditions]?.label ?? d.conditions}</Tag>
            {d.attempt > 1 && <Tag>Attempt {d.attempt}</Tag>}
          </div>
        </div>
        <div className="text-right">
          <div className="font-serif text-[28px] num leading-none">{d.total ?? "—"}<span className="text-faint text-[17px]">/{d.max_total}</span></div>
          <div className="text-[13px] mt-1 text-muted">{d.grade_status === "published" ? "Released to the student" : d.includes_unconfirmed_ai ? "Includes suggestions you haven't confirmed" : d.total === null ? "Not scored yet" : "Confirmed, not released"}</div>
        </div>
      </header>

      <section aria-label="What ATHAR noticed" className="py-6 border-b border-line">
        <h2 className="text-[15px] text-muted mb-3">What ATHAR noticed</h2>
        <ul className="space-y-2.5 text-[17px] leading-relaxed max-w-[70ch]">
          <li className="flex gap-3"><span className="pt-0.5 shrink-0"><EvidenceTag kind="test" /></span><span>{f.code}</span></li>
          <li className="flex gap-3"><span className="pt-0.5 shrink-0"><EvidenceTag kind={f.ai ? "ai" : "rules"} /></span><span>{f.reasoning}</span></li>
        </ul>
        {f.conflict && <p className="mt-4 max-w-[70ch] border-l-2 border-amber pl-4 text-[16px] text-ink">{f.conflict}</p>}
      </section>

      <section className="grid lg:grid-cols-2 gap-x-10 gap-y-8 py-8 border-b border-line">
        <div className="min-w-0">
          <h2 className="text-[15px] text-muted mb-3">Their explanation{quotes.length > 0 && <span className="text-faint"> · highlighted words were quoted as evidence</span>}</h2>
          {d.explanation ? <p className="font-serif text-[19px] leading-[1.7] text-ink"><Highlighted text={d.explanation} quotes={quotes} /></p>
            : <p className="text-faint">No explanation submitted.</p>}
          {d.ai_use_disclosure && <p className="text-[14px] text-muted mt-4">Outside help they disclosed: {d.ai_use_disclosure}</p>}
        </div>
        <div className="min-w-0">
          <h2 className="text-[15px] text-muted mb-3">Their code</h2>
          <CodeBlock code={d.code} />
          <div className="mt-4">
            <div className="text-[15px] text-ink mb-2">{f.failing.length === 0 ? `All ${d.tests.length} tests pass` : `${f.failing.length} of ${d.tests.length} tests fail`}</div>
            <ul className="divide-y divide-line text-[14px]">
              {(showAllTests ? d.tests : f.failing).map((t) => (
                <li key={t.id} className="py-2 grid grid-cols-[18px_minmax(0,1fr)_auto] gap-x-3 items-baseline">
                  <span aria-label={t.status} className={t.status === "pass" ? "text-accent-ink" : "text-brick"}>{t.status === "pass" ? "✓" : "✗"}</span>
                  <span className="font-mono text-[13.5px] break-words">{t.name}{t.hidden && <span className="text-faint font-sans"> · hidden test</span>}</span>
                  <span className="font-mono text-[13px] text-muted">{t.status === "pass" ? "" : t.error_type || `got ${t.actual}`}</span>
                </li>
              ))}
            </ul>
            <button className="link text-[14px] mt-2" onClick={() => setShowAllTests((x) => !x)}>{showAllTests ? "Show only failing tests" : `Show all ${d.tests.length} tests`}</button>
          </div>
        </div>
      </section>

      <section className="grid lg:grid-cols-[minmax(0,1fr)_400px] gap-x-12 gap-y-8 py-8">
        <Supporting d={d} f={f} />
        <Decisions d={d} onSaved={refresh} />
      </section>
    </>
  );
}

function Supporting({ d, f }: { d: Detail; f: ReturnType<typeof findings> }) {
  const r = d.reading;
  const held = d.misconceptions.filter((m) => MACHINE.includes(m.source));
  return (
    <div className="min-w-0 space-y-6">
      <h2 className="text-[15px] text-muted">The evidence behind it</h2>
      {f.testCodes.map((code) => (
        <div key={code} className="border-l-2 border-slate/60 pl-4">
          <div className="flex flex-wrap items-center gap-2"><EvidenceTag kind="test" /><span className="text-ink">Fails the way “{misconceptionLabel(code).toLowerCase()}” predicts</span></div>
          <div className="text-muted text-[14px] mt-1">{d.misconceptions.filter((m) => m.code === code && m.source === "tests").map((m) => m.detail).join(" · ")}</div>
        </div>
      ))}
      {held.map((m) => (
        <div key={m.id} className="border-l-2 border-dashed border-amber/70 pl-4">
          <div className="flex flex-wrap items-center gap-2"><EvidenceTag kind={sourceKind(m.source)} /><span className="text-ink">Possibly: {misconceptionLabel(m.code).toLowerCase()}</span></div>
          <blockquote className="font-serif text-[17px] text-ink mt-1.5">“{m.quote}”</blockquote>
        </div>
      ))}
      {r && r.rejected_ideas.length > 0 && (
        <p className="text-[14px] text-muted"><span className="text-faint">The reader thinks the student argues against: </span>{r.rejected_ideas.map((x) => misconceptionLabel(x.code).toLowerCase()).join("; ")}.</p>
      )}
      {r && (r.contradictions.length > 0 || r.missing_evidence.length > 0) && (
        <div className="grid sm:grid-cols-2 gap-6 text-[14px]">
          {r.contradictions.length > 0 && <div><div className="text-ink mb-1">Conflicts the reader saw</div><ul className="text-muted list-disc ml-4 space-y-1">{r.contradictions.map((c) => <li key={c}>{c}</li>)}</ul></div>}
          {r.missing_evidence.length > 0 && <div><div className="text-ink mb-1">What would settle it</div><ul className="text-muted list-disc ml-4 space-y-1">{r.missing_evidence.slice(0, 3).map((c) => <li key={c}>{c}</li>)}</ul></div>}
        </div>
      )}
      {!f.testCodes.length && !held.length && !r && <p className="text-muted">No flags on this submission.</p>}
      {r && (
        <details className="text-[14px]">
          <summary className="cursor-pointer text-muted hover:text-ink">Full {r.source === "ai" ? "AI" : "rule"} reading</summary>
          <div className="mt-3 space-y-2 text-muted">
            {r.summary && <p className="text-ink">{r.summary}</p>}
            <p>Reader: {r.reader}{r.prompt_version ? ` · ${r.prompt_version}` : ""} · failing tests read as: {r.code_issue.replaceAll("_", " ") || "n/a"}</p>
            {r.objectives.length > 0 && <p>Learning goals: {r.objectives.filter((o, i, all) => all.findIndex((x) => x.objective_code === o.objective_code) === i).map((o) => `${objectiveLabel(o.objective_code)}: ${o.status.replace("_", " ")}`).join(" · ")}</p>}
            {r.validation_notes.length > 0 && <p className="text-brick">Removed by validation: {r.validation_notes.join(" · ")}</p>}
            <p className="text-faint">Every quote above was checked to appear word for word in the student's text.</p>
          </div>
        </details>
      )}
    </div>
  );
}

function Decisions({ d, onSaved }: { d: Detail; onSaved: (d: Detail) => void }) {
  const published = d.grade_status === "published";
  const qc = useQueryClient();
  const confirm = useMutation({
    mutationFn: (ids: number[]) => api<{ submission: Detail }>(`/api/professor/submissions/${d.id}/confirm-ai`, { method: "POST", json: { criterion_ids: ids } }),
    onSuccess: (r) => onSaved(r.submission),
  });
  const publish = useMutation({
    mutationFn: () => api(`/api/professor/assignments/${d.assignment_id}/publish`, { method: "POST", json: { submission_ids: [d.id] } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["submission", String(d.id)] }),
  });
  return (
    <aside className="min-w-0 lg:border-l lg:border-line lg:pl-8" aria-label="Your decision">
      <h2 className="text-[15px] text-muted mb-1">Your decision</h2>
      <p className="text-[13.5px] text-faint mb-3">Suggestions count only after you accept or change them.</p>
      <ul className="divide-y divide-line">
        {d.criteria.map((c) => <CriterionRow key={c.id} d={d} c={c} onSaved={onSaved} onAccept={() => confirm.mutate([c.id])} accepting={confirm.isPending} />)}
      </ul>
      <div className="mt-6">
        {published ? <Callout tone="accent">Released. The student can see this feedback.</Callout>
          : d.publish_blockers.length ? (
            <p className="text-[14px] text-muted">To release feedback, decide on: {d.publish_blockers.map((b) => criterionLabel(b.split(":")[0]).toLowerCase()).join(", ")}.</p>
          ) : <Button variant="primary" className="w-full justify-center" disabled={publish.isPending} onClick={() => publish.mutate()}>Release feedback to the student</Button>}
      </div>
    </aside>
  );
}

function CriterionRow({ d, c, onSaved, onAccept, accepting }: { d: Detail; c: Detail["criteria"][number]; onSaved: (d: Detail) => void; onAccept: () => void; accepting: boolean }) {
  const [mode, setMode] = useState<"view" | "edit" | "why">("view");
  const [judgment, setJudgment] = useState<"met" | "partial" | "not_met">("met");
  const [points, setPoints] = useState(String(c.max_points));
  const [note, setNote] = useState("");
  const save = useMutation({
    mutationFn: () => api<Detail>(`/api/professor/submissions/${d.id}/decisions`, { method: "POST", json: { criterion_id: c.id, judgment, points: Number(points), note } }),
    onSuccess: (r) => { setMode("view"); onSaved(r); },
  });
  const latest = new Map<string, Evidence>();
  c.evidence.forEach((e) => latest.set(e.source, e));
  const current = c.state.source ? latest.get(c.state.source) : undefined;
  const suggestion = !!c.state.source && MACHINE.includes(c.state.source) && ["met", "partial", "not_met"].includes(c.state.judgment ?? "");
  const published = d.grade_status === "published";
  const sourceText = c.state.source === "professor" ? "Your decision" : c.state.source === "tests" ? "From tests" : c.state.source === "ai" ? "AI suggestion" : c.state.source === "baseline" ? "Rule suggestion" : "Rule";

  return (
    <li className="py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-ink text-[15px]" title={`${c.code}: ${c.description}`}>{criterionLabel(c.code)}</div>
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <JudgmentMark judgment={c.state.judgment} />
            {c.state.source && <EvidenceTag kind={sourceKind(c.state.source)}>{sourceText}</EvidenceTag>}
          </div>
        </div>
        <div className="num text-[15px] shrink-0">{c.state.points ?? "—"}<span className="text-faint">/{c.max_points}</span></div>
      </div>
      {mode === "why" && current && <p className="text-[14px] text-muted mt-2">{current.rationale}</p>}
      {!published && mode !== "edit" && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[14px]">
          {suggestion && <button className="link" onClick={onAccept} disabled={accepting}>Accept</button>}
          <button className="link" onClick={() => setMode("edit")}>{c.state.source === "professor" || suggestion ? "Change" : c.method === "tests" ? "Override" : "Decide"}</button>
          {current?.rationale && <button className="text-faint hover:text-ink" onClick={() => setMode(mode === "why" ? "view" : "why")}>{mode === "why" ? "Hide reason" : "Why?"}</button>}
        </div>
      )}
      {mode === "edit" && (
        <div className="mt-3 p-3 bg-surface border border-line rounded-md space-y-2.5">
          <div className="flex flex-wrap gap-2 items-center">
            {(["met", "partial", "not_met"] as const).map((j) => (
              <button key={j} onClick={() => { setJudgment(j); setPoints(String(j === "met" ? c.max_points : j === "partial" ? c.max_points / 2 : 0)); }}
                className={cx("h-8 px-3 rounded text-[13.5px] border", judgment === j ? "border-accent-strong text-ink bg-accent-wash" : "border-line-strong text-muted")}>
                {j === "not_met" ? "Not met" : j[0].toUpperCase() + j.slice(1)}
              </button>
            ))}
            <label className="text-[13.5px] text-muted ml-auto flex items-center gap-1.5">Points
              <input type="number" min={0} max={c.max_points} step={0.5} value={points} onChange={(e) => setPoints(e.target.value)} className="w-16 h-8 bg-canvas border border-line-strong rounded px-2 num text-ink" />
            </label>
          </div>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Comment for the student (optional)" className="w-full bg-canvas border border-line-strong rounded px-2 py-1.5 text-[14px] placeholder:text-faint" />
          {save.error && <div className="text-brick text-[13.5px]">{(save.error as Error).message}</div>}
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" onClick={() => setMode("view")}>Cancel</Button>
            <Button variant="primary" disabled={save.isPending} onClick={() => save.mutate()}>Save</Button>
          </div>
        </div>
      )}
    </li>
  );
}
