import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Evidence, SubmissionDetail } from "../../lib/types";
import {
  Button, CONDITIONS, Callout, CodeBlock, Crumb, ErrorState, Highlighted, JudgmentMark, Loading, Section, SourceTag, SynthTag, Tag, cx,
} from "../../components/ui";

const REASON: Record<string, string> = {
  quote_not_found: "AI quoted text that isn't in the submission (removed)",
  no_supporting_quote: "No verbatim support",
  low_confidence: "Low confidence",
  unclear: "Explanation too vague to judge",
  ai_unavailable: "Not analysed: no AI provider",
  ai_failed: "AI call failed",
  code_did_not_load: "Code did not load",
  ai_output_partially_rejected: "Part of the AI output was rejected",
  missing_from_ai_output: "AI skipped this criterion",
  rule_baseline: "Rule-based reading: confirm it yourself",
};

type Detail = SubmissionDetail;

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
  const confirm = useMutation({
    mutationFn: () => api<{ accepted: string[]; skipped: { code: string; reason: string }[]; submission: Detail }>(
      `/api/professor/submissions/${submissionId}/confirm-ai`, { method: "POST", json: {} }),
    onSuccess: (r) => refresh(r.submission),
  });
  const publish = useMutation({
    mutationFn: (d: Detail) => api<{ published: number[]; blocked: { reasons: string[] }[] }>(
      `/api/professor/assignments/${d.assignment_id}/publish`, { method: "POST", json: { submission_ids: [d.id] } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: key }),
  });

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const d = q.data!;
  const quotes = [...d.criteria.flatMap((c) => c.evidence.flatMap((e) => e.quotes)), ...d.misconceptions.map((m) => m.quote).filter(Boolean)];
  const hasAiSuggestions = d.criteria.some((c) => (c.state.source === "ai" || c.state.source === "baseline") && ["met", "partial", "not_met"].includes(c.state.judgment ?? ""));
  const published = d.grade_status === "published";

  return (
    <>
      <div className="text-[13px] text-faint mb-5">
        <Crumb to="/p">Courses</Crumb> / <Crumb to={`/p/assignments/${d.assignment_id}?tab=submissions`}>{d.assignment_title.split("—")[0].trim()}</Crumb> / Submission
      </div>
      <header className="flex flex-wrap items-end justify-between gap-4 pb-6">
        <div>
          <div className="eyebrow mb-2">Submission · attempt {d.attempt}</div>
          <h1 className="font-serif text-[28px] leading-tight">{d.student.name}</h1>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {d.is_synthetic && <SynthTag />}
            <Tag title={CONDITIONS[d.conditions]?.help}>{CONDITIONS[d.conditions]?.label ?? d.conditions}</Tag>
            <Tag tone={published ? "accent" : "neutral"}>{d.grade_status}</Tag>
          </div>
        </div>
        <div className="text-right">
          <div className="font-serif text-[30px] num leading-none">
            {d.total ?? "—"}<span className="text-faint text-[18px]">/{d.max_total}</span>
          </div>
          <div className="text-[13px] mt-1 text-muted">
            {d.total === null ? "Some criteria have no points yet" : d.includes_unconfirmed_ai ? <span className="text-amber">Includes unconfirmed AI suggestions</span> : "Every criterion confirmed"}
          </div>
        </div>
      </header>

      <div className="grid lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] gap-x-10">
        <div>
          <Section title="Written explanation" aside={quotes.length ? "Highlighted: spans cited as evidence" : undefined}>
            {d.explanation ? (
              <p className="font-serif text-[16.5px] leading-[1.7] text-ink max-w-prose"><Highlighted text={d.explanation} quotes={quotes} /></p>
            ) : <p className="text-faint">No explanation submitted.</p>}
            {d.ai_use_disclosure && (
              <p className="text-[13.5px] text-muted mt-4"><span className="text-faint">AI use disclosed by student: </span>{d.ai_use_disclosure}</p>
            )}
          </Section>
          <Section title="Code">
            <CodeBlock code={d.code} />
          </Section>
          <Section title="Test results" aside={`${d.tests.filter((t) => t.status === "pass").length} of ${d.tests.length} passed`}>
            <table className="w-full text-[13.5px]">
              <tbody className="divide-y divide-line">
                {d.tests.map((t) => (
                  <tr key={t.id}>
                    <td className="py-2 pr-3 w-14">
                      <span className={cx("text-2xs font-medium", t.status === "pass" ? "text-accent-ink" : "text-brick")}>{t.status.toUpperCase()}</span>
                    </td>
                    <td className="py-2 pr-3 font-mono">{t.name}{t.hidden && <span className="text-faint font-sans"> · hidden</span>}</td>
                    <td className="py-2 font-mono text-muted text-right">
                      {t.status === "pass" ? "" : t.error_type ? <span title={t.error_message}>{t.error_type}</span> : <>got {t.actual}</>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
          {d.misconceptions.length > 0 && (
            <Section title="Misconception evidence">
              <ul className="space-y-3 text-[14px]">
                {d.misconceptions.map((m) => (
                  <li key={m.id}>
                    <div className="flex items-center gap-2"><span className="font-mono text-[11.5px] text-brick">{m.code}</span><SourceTag source={m.source} /></div>
                    <div className="text-muted mt-0.5">{m.source === "ai" ? <>“{m.quote}”. {m.detail}</> : m.detail}</div>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        <div>
          <Section title="Rubric review" aside={hasAiSuggestions && !published ? (
            <button className="link" disabled={confirm.isPending} onClick={() => confirm.mutate()}>Accept all machine suggestions</button>
          ) : undefined}>
            {confirm.data && confirm.data.skipped.length > 0 && (
              <div className="mb-4"><Callout tone="amber">Not accepted: {confirm.data.skipped.map((s) => `${s.code} (${s.reason})`).join(", ")}. Decide these yourself.</Callout></div>
            )}
            <div className="space-y-6">
              {d.criteria.map((c) => <CriterionReview key={c.id} sub={d} c={c} onSaved={refresh} />)}
            </div>
          </Section>
          <Section title="Publish">
            {published ? <Callout tone="accent">Published. The student can see this feedback.</Callout> : d.publish_blockers.length ? (
              <Callout tone="amber" title="Not ready to publish">
                <ul className="list-disc ml-4">{d.publish_blockers.map((b) => <li key={b}>{b}</li>)}</ul>
              </Callout>
            ) : (
              <div className="flex items-center justify-between gap-4">
                <p className="text-muted text-[14px]">Every criterion rests on tests or your decision.</p>
                <Button variant="primary" disabled={publish.isPending} onClick={() => publish.mutate(d)}>Publish feedback</Button>
              </div>
            )}
          </Section>
        </div>
      </div>
    </>
  );
}

function CriterionReview({ sub, c, onSaved }: { sub: Detail; c: Detail["criteria"][number]; onSaved: (d: Detail) => void }) {
  const [editing, setEditing] = useState(false);
  const [judgment, setJudgment] = useState<"met" | "partial" | "not_met">("met");
  const [points, setPoints] = useState<string>(String(c.max_points));
  const [note, setNote] = useState("");
  const save = useMutation({
    mutationFn: () => api<Detail>(`/api/professor/submissions/${sub.id}/decisions`, {
      method: "POST", json: { criterion_id: c.id, judgment, points: Number(points), note },
    }),
    onSuccess: (d) => { setEditing(false); onSaved(d); },
  });
  const latestBySource = new Map<string, Evidence>();
  c.evidence.forEach((e) => latestBySource.set(e.source, e));
  const shown = ["professor", "tests", "rules", "ai"].map((s) => latestBySource.get(s)).filter(Boolean) as Evidence[];

  return (
    <div className="border-b border-line pb-5 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-ink"><span className="font-mono text-[13px] text-accent-ink mr-2">{c.code}</span>{c.title}</div>
          <div className="text-[13px] text-faint mt-0.5">{c.method === "tests" ? "Scored by tests" : "AI suggests, you decide"} · {c.max_points} pts</div>
        </div>
        <div className="text-right shrink-0">
          <JudgmentMark judgment={c.state.judgment} />
          <div className="num text-[14px] mt-0.5">{c.state.points ?? "—"}<span className="text-faint">/{c.max_points}</span></div>
        </div>
      </div>
      <ul className="mt-3 space-y-3">
        {shown.map((e) => (
          <li key={e.id} className={cx("text-[14px]", e.source !== c.state.source && "opacity-60")}>
            <div className="flex flex-wrap items-center gap-1.5 mb-1">
              {!["ai_unavailable", "ai_failed"].includes(e.judgment) && <SourceTag source={e.source} />}
              {(e.source === "ai" || e.source === "baseline") && e.confidence && <span className="text-2xs text-faint">confidence {e.confidence}</span>}
              {e.review_reasons.map((r) => <Tag key={r} tone={r.startsWith("ai_") || r === "quote_not_found" ? "brick" : "amber"}>{REASON[r] ?? r}</Tag>)}
              {e.source !== c.state.source && <span className="text-2xs text-faint">superseded</span>}
            </div>
            <p className="text-muted">{e.rationale}</p>
          </li>
        ))}
      </ul>
      {sub.grade_status !== "published" && (
        editing ? (
          <div className="mt-3 p-3 bg-surface border border-line rounded-md space-y-2.5">
            <div className="flex flex-wrap gap-2 items-center">
              {(["met", "partial", "not_met"] as const).map((j) => (
                <button key={j} onClick={() => { setJudgment(j); setPoints(String(j === "met" ? c.max_points : j === "partial" ? c.max_points / 2 : 0)); }}
                  className={cx("h-7 px-2.5 rounded text-[13.5px] border", judgment === j ? "border-accent-strong text-ink bg-accent-wash" : "border-line-strong text-muted")}>
                  {j === "not_met" ? "Not met" : j[0].toUpperCase() + j.slice(1)}
                </button>
              ))}
              <label className="text-[13.5px] text-muted ml-auto flex items-center gap-1.5">
                Points
                <input type="number" min={0} max={c.max_points} step={0.5} value={points} onChange={(e) => setPoints(e.target.value)}
                  className="w-16 h-7 bg-canvas border border-line-strong rounded px-2 num text-ink" />
              </label>
            </div>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Comment for the student (optional)"
              className="w-full bg-canvas border border-line-strong rounded px-2 py-1.5 text-[14px] placeholder:text-faint" />
            {save.error && <div className="text-brick text-[13.5px]">{(save.error as Error).message}</div>}
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
              <Button variant="primary" disabled={save.isPending} onClick={() => save.mutate()}>Save decision</Button>
            </div>
          </div>
        ) : (
          <button className="link text-[13.5px] mt-3" onClick={() => setEditing(true)}>
            {c.state.source === "professor" ? "Change your decision" : c.method === "tests" ? "Override" : "Decide"}
          </button>
        )
      )}
    </div>
  );
}
