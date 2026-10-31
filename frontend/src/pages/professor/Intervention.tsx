import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { EvidenceTag } from "../../components/Evidence";
import type { Intervention, InterventionStudent, Item, Outcome } from "../../lib/types";
import { Button, Callout, CodeBlock, Crumb, ErrorState, Loading, Section, SynthTag, Tag, cx, fmtDate } from "../../components/ui";

export const OUTCOME: Record<Outcome, { label: string; tone: "accent" | "amber" | "neutral"; dot: string }> = {
  demonstrated: { label: "Demonstrated on this task", tone: "accent", dot: "bg-accent-strong" },
  still_developing: { label: "Still developing", tone: "amber", dot: "bg-amber" },
  insufficient_evidence: { label: "Insufficient evidence", tone: "neutral", dot: "border border-faint" },
};

const KIND_LABEL: Record<string, string> = {
  concept_practice: "Concept practice", debugging: "Debugging exercise", explain_reasoning: "Explain-your-reasoning task",
};

export function InterventionPage() {
  const { interventionId } = useParams();
  const qc = useQueryClient();
  const key = ["intervention", interventionId];
  const q = useQuery({ queryKey: key, queryFn: () => api<Intervention>(`/api/professor/interventions/${interventionId}`) });
  const set = (iv: Intervention) => { qc.setQueryData(key, iv); qc.invalidateQueries({ queryKey: ["course"] }); };
  const act = useMutation({
    mutationFn: (path: string) => api<Intervention | { intervention: Intervention }>(`/api/professor/interventions/${interventionId}/${path}`, { method: "POST" }),
    onSuccess: (r) => set("intervention" in r ? r.intervention : r),
  });

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const iv = q.data!;

  return (
    <>
      <div className="text-[13px] text-faint mb-5">
        <Crumb to="/p">Courses</Crumb> / <Crumb to={`/p/courses/${iv.course_id}`}>{iv.course_code}</Crumb> /{" "}
        <Crumb to={`/p/assignments/${iv.assignment.id}?tab=plan`}>{iv.assignment.title.split("—")[0].trim()}</Crumb> /{" "}
        {iv.insight_id ? <><Crumb to={`/p/insights/${iv.insight_id}`}>Insight</Crumb> / </> : null}Intervention
      </div>
      <header className="pb-6">
        <div className="eyebrow mb-2">{KIND_LABEL[iv.kind]}{iv.misconception_code ? ` · ${iv.misconception_code}` : ""}</div>
        <h1 className="font-serif text-[32px] leading-[1.15] tracking-[-0.01em]">{iv.title}</h1>
        <p className="text-muted mt-2">For {iv.target_student_ids.length} students, from {iv.assignment.title}.</p>
      </header>

      {/* The loop for this intervention: evidence → plan → approval → delivery → verification */}
      {iv.status === "rejected" ? (
        <p className="py-3 border-y border-line text-brick text-[14px]">Rejected. Nothing was sent to students.</p>
      ) : (
        <ol className="grid grid-cols-2 md:grid-cols-5 border-y border-line" aria-label="Intervention progress">
          {[
            { label: "Evidence", value: `${iv.target_student_ids.length} students`, sub: "from tests and readings", on: true },
            { label: "Plan", value: iv.explanation_source.startsWith("ai:") ? "AI draft" : "Template", sub: "you can edit it", on: true },
            { label: "Your approval", value: iv.approved_at ? fmtDate(iv.approved_at) : "Waiting", sub: iv.approved_at ? "approved" : "nothing sent yet", on: !!iv.approved_at },
            { label: "Delivered", value: `${iv.progress.delivered} activities`, sub: "one per student", on: iv.progress.delivered > 0 },
            { label: "Verified", value: `${iv.progress.verified} new attempts`, sub: "checked by fixed rules", on: iv.progress.verified > 0 },
          ].map((x, i) => (
            <li key={x.label} className={cx("py-4 pr-4 border-t-2 -mt-px", x.on ? "border-accent-strong" : "border-transparent")}>
              <div className="text-[12.5px] text-faint num">{i + 1} · {x.label}</div>
              <div className={cx("text-[15.5px] mt-1", x.on ? "text-ink" : "text-faint")}>{x.value}</div>
              <div className="text-[13px] text-faint">{x.sub}</div>
            </li>
          ))}
        </ol>
      )}

      {act.error && <div className="mt-4"><Callout tone="brick" title="That didn't go through">{(act.error as Error).message}</Callout></div>}
      {iv.execution_error && <div className="mt-4"><Callout tone="brick" title="Execution failed and was rolled back">{iv.execution_error}</Callout></div>}

      {iv.status === "draft" ? <DraftView iv={iv} onSaved={set} act={act} /> : <LiveView iv={iv} act={act} />}
    </>
  );
}

// ------------------------------------------------------------------ draft

function DraftView({ iv, onSaved, act }: { iv: Intervention; onSaved: (iv: Intervention) => void; act: ReturnType<typeof useMutation<Intervention | { intervention: Intervention }, Error, string>> }) {
  const [text, setText] = useState(iv.explanation);
  const [targets, setTargets] = useState<Set<number>>(new Set(iv.target_student_ids));
  const [followup, setFollowup] = useState(iv.followup_item?.id ?? null);
  useEffect(() => { setText(iv.explanation); }, [iv.explanation]);
  const dirty = text !== iv.explanation || targets.size !== iv.target_student_ids.length || followup !== (iv.followup_item?.id ?? null);
  const save = useMutation({
    mutationFn: () => api<Intervention>(`/api/professor/interventions/${iv.id}`, {
      method: "PATCH", json: { explanation: text, target_student_ids: [...targets], followup_item_id: followup },
    }),
    onSuccess: onSaved,
  });
  const chosen = iv.followup_options.find((o) => o.id === followup) ?? iv.followup_item;
  const canApprove = !dirty && targets.size > 0 && (iv.kind === "explain_reasoning" || !!chosen?.validation.valid);

  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-x-12">
      <div>
        <Section title="1 · What students will read first" aside={<SourceLabel source={iv.explanation_source} />}>
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={12}
            className="w-full bg-surface border border-line-strong rounded-md p-4 font-serif text-[16px] leading-[1.7] text-ink" />
          <p className="text-[13px] text-faint mt-2">Edit freely. Students see exactly this text.</p>
        </Section>

        {iv.practice_item && (
          <Section title="2 · Guided practice (assisted)" aside="AI help and hints are part of this step">
            <ItemSummary item={iv.practice_item} />
            <div className="mt-4">
              <div className="eyebrow mb-2">Progressive hints, revealed one at a time</div>
              <ol className="space-y-1.5 text-[14px] text-muted list-decimal ml-5">{iv.practice_item.hints.map((h) => <li key={h}>{h}</li>)}</ol>
            </div>
          </Section>
        )}

        {iv.kind === "explain_reasoning" ? (
          <Section title="2 · What students will do" aside="Unsupervised">
            <p className="text-muted max-w-prose">
              Each student sees their own Assignment 3 code and explains, in writing, exactly when and why it stops and what power(5, 0) returns.
              Their code is not re-run or re-graded. The explanation is read by the configured reader, and fixed rules decide the outcome:
              a clear stopping condition means demonstrated, a stated misconception means still developing, and anything vague means insufficient evidence.
            </p>
          </Section>
        ) : iv.kind === "debugging" ? (
          <Section title="2 · Debugging exercise" aside="Checked by tests">
            {iv.followup_item && <ItemSummary item={iv.followup_item} brokenLabel="Broken starting code" />}
          </Section>
        ) : (
        <Section title="3 · Follow-up check (unsupervised)" aside="A different problem that tests the same idea">
          <GenerateCheck ivId={iv.id} onDone={onSaved} />
          <div className="space-y-3">
            {iv.followup_options.map((o) => (
              <label key={o.id} className={cx("block border rounded-md p-4 cursor-pointer transition-colors",
                followup === o.id ? "border-accent-strong bg-accent-wash/40" : "border-line-strong hover:bg-surface")}>
                <div className="flex items-start gap-3">
                  <input type="radio" name="followup" className="mt-1.5 accent-[rgb(var(--accent-strong))]" checked={followup === o.id}
                    onChange={() => setFollowup(o.id)} disabled={!o.validation.valid} />
                  <div className="min-w-0 flex-1"><ItemSummary item={o} /></div>
                </div>
              </label>
            ))}
          </div>
        </Section>
        )}
      </div>

      <aside className="lg:pt-6 space-y-8">
        <div className="lg:sticky lg:top-6 space-y-6">
          <div>
            <div className="eyebrow mb-2">Students ({targets.size} of {iv.students.length})</div>
            <ul className="max-h-[320px] overflow-y-auto pr-1 space-y-1 text-[14px]">
              {iv.students.map((s) => (
                <li key={s.student_id}>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={targets.has(s.student_id)} className="accent-[rgb(var(--accent-strong))]"
                      onChange={(e) => { const n = new Set(targets); e.target.checked ? n.add(s.student_id) : n.delete(s.student_id); setTargets(n); }} />
                    <span className="text-muted">{s.name}</span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
          <div className="border-t border-line pt-5 space-y-3">
            {dirty && <Button className="w-full justify-center" onClick={() => save.mutate()} disabled={save.isPending}>Save changes</Button>}
            {save.error && <p className="text-brick text-[13px]">{(save.error as Error).message}</p>}
            <Button variant="primary" className="w-full justify-center" disabled={!canApprove || act.isPending} onClick={() => act.mutate("approve")}>
              {act.isPending ? "Sending…" : `Approve and send to ${targets.size} students`}
            </Button>
            <p className="text-[13px] text-faint leading-5">
              Approving creates the follow-up check and one activity per student, right away. Nothing reaches students before you approve.
              {iv.kind !== "explain_reasoning" && !chosen?.validation.valid && " The selected check hasn't passed validation."}{dirty && " Save your changes first."}
            </p>
            <button className="text-[13px] text-faint hover:text-brick" onClick={() => act.mutate("reject")}>Reject this draft</button>
          </div>
        </div>
      </aside>
    </div>
  );
}

function SourceLabel({ source }: { source: string }) {
  if (source.startsWith("ai:")) return <Tag tone="amber">AI draft · {source.slice(3)}</Tag>;
  if (source.startsWith("template")) return <Tag title={source}>Template draft (no AI)</Tag>;
  return <Tag>{source}</Tag>;
}

function GenerateCheck({ ivId, onDone }: { ivId: number; onDone: (iv: Intervention) => void }) {
  const gen = useMutation({
    mutationFn: () => api<{ item: Item; intervention: Intervention }>(`/api/professor/interventions/${ivId}/generate-check`, { method: "POST" }),
    onSuccess: (r) => onDone(r.intervention),
  });
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <p className="text-[13.5px] text-faint max-w-prose">
        Options come from your validated item bank. You can also ask the AI for a new problem; it only becomes selectable if the sandbox confirms
        correct code passes and code with the misconception fails.
      </p>
      <Button onClick={() => gen.mutate()} disabled={gen.isPending}>{gen.isPending ? "Generating and validating…" : "Generate a new check with AI"}</Button>
      {gen.error && <p className="w-full text-[13px] text-amber">{(gen.error as Error).message}</p>}
      {gen.data && !gen.data.item.validation.valid && (
        <p className="w-full text-[13px] text-brick">The AI's proposal was rejected: {gen.data.item.validation.problems.join(" ")}</p>
      )}
    </div>
  );
}

function ItemSummary({ item, brokenLabel }: { item: Item; brokenLabel?: string }) {
  const [open, setOpen] = useState(false);
  const v = item.validation;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-ink">{item.title}</span>
        <Tag tone={item.source.startsWith("ai:") ? "amber" : "neutral"}>{item.source === "item_bank" ? "From your item bank" : `AI-generated · ${item.source.slice(3)}`}</Tag>
        {v.valid ? <Tag tone="accent">Validated</Tag> : <Tag tone="brick">Failed validation</Tag>}
      </div>
      <p className="text-muted text-[14px] mt-1.5 max-w-prose">{item.prompt}</p>
      <div className="grid sm:grid-cols-2 gap-3 mt-3 text-[13.5px]" aria-label="Validation result">
        <div className={cx("rounded-md border px-3 py-2.5", v.reference_passed === v.total && v.total > 0 ? "border-accent/60 bg-accent-wash/40" : "border-brick/50")}>
          <div className="text-faint">{brokenLabel ? "Fixed version" : "Correct solution"}</div>
          <div className="text-ink mt-0.5">{v.reference_passed === v.total && v.total > 0 ? "✓" : "✗"} passes {v.reference_passed} of {v.total} tests</div>
        </div>
        <div className={cx("rounded-md border px-3 py-2.5", v.misconception_caught_by.length ? "border-accent/60 bg-accent-wash/40" : "border-brick/50")}>
          <div className="text-faint">{brokenLabel ?? "Code with the misconception"}</div>
          <div className="text-ink mt-0.5">{v.misconception_caught_by.length ? <>✓ caught: <span className="font-mono text-[12.5px] text-muted">{v.misconception_caught_by.join(", ")}</span></> : "✗ not caught, so this check can't tell them apart"}</div>
        </div>
      </div>
      {v.problems.length > 0 && <ul className="text-brick text-[13px] mt-1 list-disc ml-4">{v.problems.map((p) => <li key={p}>{p}</li>)}</ul>}
      <button type="button" className="link text-[13px] mt-2" onClick={(e) => { e.preventDefault(); setOpen((x) => !x); }}>
        {open ? "Hide" : "Show"} solutions and tests
      </button>
      {open && (
        <div className="grid md:grid-cols-2 gap-3 mt-3">
          <div><div className="eyebrow mb-1">Reference</div><CodeBlock code={item.reference_solution} /></div>
          <div><div className="eyebrow mb-1">{brokenLabel ?? "With the misconception"}</div><CodeBlock code={item.misconception_solution} /></div>
          <ul className="md:col-span-2 font-mono text-[12px] text-muted space-y-0.5">
            {item.tests.map((t) => <li key={t.name}>{t.name}{t.hidden ? " · hidden" : ""}{t.probes.length ? " · probe" : ""}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ active / completed

function LiveView({ iv, act }: { iv: Intervention; act: ReturnType<typeof useMutation<Intervention | { intervention: Intervention }, Error, string>> }) {
  const p = iv.progress;
  const [filter, setFilter] = useState<Outcome | "waiting" | "all">("all");
  const rows = iv.students.filter((s) =>
    filter === "all" ? true : filter === "waiting" ? !s.verification : s.verification?.outcome === filter);
  const hasSynthPending = iv.students.some((s) => s.is_synthetic && !s.is_demo_persona && !s.verification);

  return (
    <div className="pt-2">
      <div className="grid grid-cols-2 md:grid-cols-5 border-b border-line divide-x divide-line">
        {[
          ["Delivered", p.delivered, ""],
          ["Started", p.started, ""],
          ["Demonstrated", p.demonstrated, "text-accent-ink"],
          ["Still developing", p.still_developing, "text-amber"],
          ["Insufficient evidence", p.insufficient_evidence, "text-muted"],
        ].map(([k, v, c]) => (
          <div key={k as string} className="py-4 px-4 first:pl-0">
            <div className={cx("font-serif text-[28px] leading-none num", c as string)}>{v}</div>
            <div className="text-[13px] text-muted mt-1.5">{k}</div>
          </div>
        ))}
      </div>
      {p.simulated > 0 && (
        <p className="text-[13px] text-faint mt-3">
          {p.simulated} of these attempts are simulated synthetic classmates, sent through the real grading and verification path. Their outcomes were computed, not scripted.
        </p>
      )}

      <div className="grid lg:grid-cols-[minmax(0,1fr)_300px] gap-x-12">
        <div>
          <Section title="Students" aside={
            <span className="flex gap-1">
              {(["all", "demonstrated", "still_developing", "insufficient_evidence", "waiting"] as const).map((f) => (
                <button key={f} onClick={() => setFilter(f)} className={cx("px-2 h-6 rounded text-[12.5px]", filter === f ? "bg-raised text-ink" : "text-faint hover:text-ink")}>
                  {f === "all" ? "All" : f === "waiting" ? "Waiting" : OUTCOME[f].label.split(" ")[0]}
                </button>
              ))}
            </span>
          }>
            <ul className="divide-y divide-line">
              {rows.map((s) => <StudentRow key={s.student_id} s={s} />)}
            </ul>
          </Section>
        </div>
        <aside className="lg:pt-6 space-y-8 text-[14px]">
          {iv.recommendations.length > 0 && (
            <div>
              <div className="eyebrow mb-2">Suggested next steps</div>
              <ul className="space-y-2.5">{iv.recommendations.map((r) => <li key={r} className="text-muted border-l-2 border-accent-strong pl-3">{r}</li>)}</ul>
              <p className="text-[12.5px] text-faint mt-2">Computed from verified outcomes by fixed rules. You decide what happens next.</p>
            </div>
          )}
          <div>
            <div className="eyebrow mb-2">How outcomes are decided</div>
            {iv.kind !== "concept_practice" ? (
              <p className="text-faint leading-5">
                {iv.kind === "debugging"
                  ? "Demonstrated means the fixed program runs and passes every test. Anything less is still developing."
                  : "Only the explanation is assessed. A clear, explicit stopping condition is demonstrated; a stated misconception is still developing; vague or unread reasoning is insufficient evidence."}
              </p>
            ) : <p className="text-faint leading-5">
              <span className="text-muted">Demonstrated</span> needs both: every test passes, including the smallest input, and the written reasoning names the stopping condition.
              Failing a probe the way the misconception predicts means <span className="text-muted">still developing</span>.
              Working code with missing or vague reasoning is <span className="text-muted">insufficient evidence</span>. One task never proves lasting mastery.
            </p>}
          </div>
          <div>
            <div className="eyebrow mb-2">What students received</div>
            <p className="text-muted">{iv.kind === "explain_reasoning" ? "A written explanation of their own Assignment 3 code." :
              iv.kind === "debugging" ? `${iv.followup_item?.title}: fix the program until every test passes.` :
              `${iv.practice_item?.title} with ${iv.practice_item?.hints.length} hints, then ${iv.followup_item?.title}.`}</p>
            {iv.followup_assignment_id && <p className="text-faint text-[13px] mt-1">Follow-up assignment #{iv.followup_assignment_id} · unsupervised</p>}
          </div>
          {iv.status === "active" && (
            <div className="border-t border-line pt-5 space-y-3">
              {hasSynthPending && (
                <div>
                  <Button className="w-full justify-center" onClick={() => act.mutate("simulate")} disabled={act.isPending}>
                    Simulate synthetic classmates
                  </Button>
                  <p className="text-[12.5px] text-faint mt-2 leading-5">
                    Demo only. Fictional classmates submit varied attempts through the same path as Sara. Demo personas are never simulated.
                  </p>
                </div>
              )}
              <button className="text-[13px] text-faint hover:text-ink" onClick={() => act.mutate("complete")}>Close this intervention</button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function StudentRow({ s }: { s: InterventionStudent }) {
  const v = s.verification;
  const t = s.task;
  const status = !t ? "Not delivered" : v ? null : t.status === "assigned" ? "Not opened yet" : "Working on it";
  const practice = t && !t.is_simulated
    ? [t.has_initial && "wrote first thoughts", t.practice_attempts > 0 && `${t.practice_attempts} practice runs`,
       t.hints_revealed > 0 && `${t.hints_revealed} hints`, t.has_revised && "revised answer"].filter(Boolean).join(" · ")
    : "";
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-ink text-[15.5px]">{s.name}</span>
        {s.is_demo_persona ? <Tag tone="slate">Demo persona</Tag> : s.is_synthetic && <SynthTag />}
        {t?.is_simulated && <Tag>Simulated attempt</Tag>}
      </div>
      <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-3 text-[13.5px]">
        <div className="border-l-2 border-line-strong pl-3">
          <div className="text-faint">Before · Assignment 3</div>
          <div className="text-muted mt-0.5">{s.before.map((b) => b.source === "tests" ? b.detail : `“${b.quote}”`).join(" · ") || "—"}</div>
          {practice && <div className="text-faint mt-1">Practice (assisted): {practice}</div>}
        </div>
        <div className={cx("pl-3 border-l-2", v ? (v.outcome === "demonstrated" ? "border-accent-strong" : v.outcome === "still_developing" ? "border-amber" : "border-line-strong") : "border-line")}>
          <div className="text-faint">After · new independent check</div>
          {v ? (
            <>
              <div className="text-ink mt-0.5 flex flex-wrap items-center gap-2"><EvidenceTag kind="verified">{OUTCOME[v.outcome].label}</EvidenceTag>
                <span className="text-faint num">{v.tests_passed}/{v.tests_total} tests · reasoning {v.explanation_judgment.replace("_", " ") || "—"}</span></div>
              <div className="text-muted mt-1">{v.reasons[0]}</div>
              <Link to={`/p/submissions/${v.submission_id}`} className="link">Open the attempt</Link>
            </>
          ) : <div className="text-faint mt-0.5">{status}</div>}
        </div>
      </div>
    </li>
  );
}
