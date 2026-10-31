import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { PlanTab } from "./Plan";
import type { AssignmentDetail, GradingRun, Insight, InsightEvidence, SubmissionRow, SupportEvidence } from "../../lib/types";
import {
  Button, CONDITIONS, Callout, CodeBlock, Crumb, Empty, ErrorState, JudgmentMark, KIND, Loading, Meter, PageHeader,
  Section, Tag, cx, fmtDate,
} from "../../components/ui";

const TABS = [
  { id: "insights", label: "Insights" },
  { id: "plan", label: "Who needs what" },
  { id: "submissions", label: "Submissions" },
  { id: "rubric", label: "Rubric & tests" },
] as const;

export function AssignmentPage() {
  const { assignmentId } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "insights";
  const q = useQuery({ queryKey: ["assignment", assignmentId], queryFn: () => api<AssignmentDetail>(`/api/professor/assignments/${assignmentId}`) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const a = q.data!;

  return (
    <>
      <div className="text-[13px] text-faint mb-5">
        <Crumb to="/p">Courses</Crumb> / <Crumb to={`/p/courses/${a.course_id}`}>{a.course_code}</Crumb> / Assignment
      </div>
      <PageHeader
        eyebrow={`${a.course_code} · Due ${fmtDate(a.due_at)}`}
        title={a.title}
      >
        <span className="flex flex-wrap gap-1.5 mt-1">
          <Tag>{KIND[a.kind] ?? a.kind}</Tag>
          <Tag title={CONDITIONS[a.conditions]?.help}>{CONDITIONS[a.conditions]?.label ?? a.conditions}</Tag>
          <Tag>{a.status === "closed" ? "Closed" : a.status}</Tag>
        </span>
      </PageHeader>

      <GradingPanel a={a} />

      <div className="flex gap-6 border-b border-line mt-8" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setParams({ tab: t.id }, { replace: true })}
            className={cx("pb-2.5 -mb-px text-[14px] border-b-2 transition-colors",
              tab === t.id ? "border-accent-strong text-ink" : "border-transparent text-muted hover:text-ink")}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "insights" && <InsightsTab a={a} />}
      {tab === "plan" && <PlanTab assignmentId={a.id} />}
      {tab === "submissions" && <SubmissionsTab a={a} />}
      {tab === "rubric" && <RubricTab a={a} />}
    </>
  );
}

// ---------------------------------------------------------------- grading run

function GradingPanel({ a }: { a: AssignmentDetail }) {
  const qc = useQueryClient();
  const [runId, setRunId] = useState<number | null>(a.latest_run && ["queued", "running"].includes(a.latest_run.status) ? a.latest_run.id : null);
  const start = useMutation({
    mutationFn: () => api<GradingRun>(`/api/professor/assignments/${a.id}/grading-runs`, { method: "POST" }),
    onSuccess: (r) => setRunId(r.id),
  });
  const poll = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api<GradingRun>(`/api/professor/grading-runs/${runId}`),
    enabled: runId !== null,
    refetchInterval: (q) => (q.state.data && !["queued", "running"].includes(q.state.data.status) ? false : 800),
  });
  const live = poll.data ?? a.latest_run;
  useEffect(() => {
    if (poll.data && !["queued", "running"].includes(poll.data.status)) {
      setRunId(null);
      qc.invalidateQueries({ queryKey: ["assignment", String(a.id)] });
      qc.invalidateQueries({ queryKey: ["insights", String(a.id)] });
      qc.invalidateQueries({ queryKey: ["submissions", String(a.id)] });
      qc.invalidateQueries({ queryKey: ["plan", a.id] });
      qc.invalidateQueries({ queryKey: ["course"] });
    }
  }, [poll.data, a.id, qc]);

  const s = a.stats;
  const running = live && ["queued", "running"].includes(live.status);
  const explanationCodes = a.criteria.filter((c) => c.method === "explanation").map((c) => c.code).join(" and ");

  return (
    <div className="border-y border-line py-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <dl className="flex flex-wrap gap-x-8 gap-y-2 text-[14px]">
          {[
            ["Submitted", `${s.submitted} / ${s.enrolled}`],
            ["Evidence prepared", s.graded],
            ["Need your review", s.needs_review],
            ["Published", s.published],
          ].map(([k, v]) => (
            <div key={k as string}>
              <dt className="text-faint text-2xs uppercase tracking-[0.1em]">{k}</dt>
              <dd className="num text-[17px] text-ink mt-0.5">{v}</dd>
            </div>
          ))}
        </dl>
        <Button variant={live ? "secondary" : "primary"} disabled={!!running || start.isPending} onClick={() => start.mutate()}>
          {running ? "Preparing…" : live ? "Re-run grading evidence" : "Prepare grading evidence"}
        </Button>
      </div>

      {start.error && <Callout tone="brick" title="Could not start">{(start.error as Error).message}</Callout>}

      {running && live && (
        <div className="space-y-2 max-w-xl">
          <div className="text-[13.5px] text-muted">
            {live.stage === "tests" || live.status === "queued"
              ? `Running tests in the sandbox: ${live.tests_done} of ${live.total || s.submitted}`
              : live.stage === "explanations"
                ? `Reading written explanations: ${live.ai_done + live.ai_failed} of ${live.total}`
                : "Connecting evidence to learning objectives"}
          </div>
          <Meter value={live.stage === "explanations" ? live.ai_done + live.ai_failed : live.tests_done} total={live.total || s.submitted} />
        </div>
      )}

      {!running && live?.status === "failed" && (
        <Callout tone="brick" title="The grading run failed">{live.error || "Unknown error"}. Nothing from this run was published.</Callout>
      )}
      {!running && live?.status === "done" && (
        <div className="text-[13.5px] text-faint">
          Evidence prepared {live.finished_at ? new Date(live.finished_at).toLocaleString() : ""}.
          {" "}Tests ran for all {live.total} submissions in an isolated process.
          {live.ai_status === "used" && ` Written explanations read by ${live.ai_provider.split(":")[1] ?? live.ai_provider}; every quoted span was checked against the student's text.`}
        </div>
      )}
      {!running && live?.status === "done" && live.ai_status === "baseline" && (
        <Callout tone="amber" title="Explanations were read by rules, not by AI">
          No model credentials are configured, so ATHAR's rule-based reader ({live.ai_provider}) read the written explanations.
          It is fast and transparent but brittle with unfamiliar phrasing: on held-out explanations it gets about half of the
          stopping-condition judgments right (see docs/EVALUATION.md). Treat these readings as leads. They never publish a grade.
        </Callout>
      )}
      {!running && live?.status === "done" && live.ai_status === "unavailable" && (
        <Callout tone="amber" title="Written explanations were not analysed">
          No AI provider is configured, so {explanationCodes} have no suggestions and need your review. Test evidence is complete.
          Misconceptions that only show up in explanations can't be detected until a provider is set in <code className="font-mono">backend/.env</code>.
        </Callout>
      )}
      {!running && live?.status === "done" && (live.ai_status === "failed" || live.ai_status === "partial") && (
        <Callout tone="brick" title={`AI analysis failed for ${live.ai_failed} submissions`}>
          Those explanations are marked "AI failed" and need your review. Re-run once the provider is reachable.
        </Callout>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- insights

function InsightsTab({ a }: { a: AssignmentDetail }) {
  const q = useQuery({
    queryKey: ["insights", String(a.id)],
    queryFn: () => api<{ run: GradingRun | null; insights: Insight[] }>(`/api/professor/assignments/${a.id}/insights`),
  });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const { run, insights } = q.data!;
  if (!run) return <Empty title="No evidence prepared yet">Prepare grading evidence to see which learning objectives this class has and hasn't demonstrated.</Empty>;
  const mis = insights.filter((i) => i.kind === "misconception");
  const support = insights.find((i) => i.kind === "needs_support");

  return (
    <div className="pt-2">
      <Section title="Possible misconceptions" aside={`Patterns found in at least ${(mis[0]?.evidence as InsightEvidence | undefined)?.threshold ?? 3} students`}>
        {mis.length === 0 ? (
          <Empty title="No shared misconception patterns found">
            None of the misconceptions authored with this rubric showed up in enough submissions to report.
          </Empty>
        ) : (
          <ul className="divide-y divide-line">
            {mis.map((i) => {
              const e = i.evidence as InsightEvidence;
              return (
                <li key={i.id}>
                  <Link to={`/p/insights/${i.id}`} className="grid grid-cols-[72px_1fr_auto] gap-5 py-5 group">
                    <div>
                      <div className="font-serif text-[32px] leading-none num">{i.student_count}</div>
                      <div className="text-2xs text-faint mt-1">students</div>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {i.objective && <span className="font-mono text-[11px] text-accent-ink">{i.objective.code}</span>}
                        <span className="text-[15px] text-ink">{i.title}</span>
                      </div>
                      <p className="text-[14px] text-muted max-w-prose">{i.summary}</p>
                      <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2 text-[13px] text-faint num">
                        <span>Tests only {e.counts.tests_only}</span>
                        <span>Explanation only {e.counts.explanation_only}</span>
                        <span>Both {e.counts.both}</span>
                        {e.counts.working_code_confused_reasoning > 0 && (
                          <span className="text-amber">Working code, confused reasoning {e.counts.working_code_confused_reasoning}</span>
                        )}
                      </div>
                    </div>
                    <span className="text-[14px] text-faint group-hover:text-accent-ink self-center">Evidence →</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Section>
      {support && <SupportBlock insight={support} />}
    </div>
  );
}

function SupportBlock({ insight }: { insight: Insight }) {
  const e = insight.evidence as SupportEvidence;
  return (
    <Section title="Students who may need direct support" aside={insight.summary}>
      <div className="grid md:grid-cols-2 gap-x-12 gap-y-4 text-[14px]">
        <div>
          <div className="eyebrow mb-2">Two or more criteria not met</div>
          {e.struggling.length === 0 ? <div className="text-faint">None</div> : (
            <ul className="space-y-1.5">
              {e.struggling.map((s) => (
                <li key={s.submission_id} className="flex justify-between gap-3">
                  <Link className="link" to={`/p/submissions/${s.submission_id}`}>{s.student_name}</Link>
                  <span className="text-faint">{s.criteria_not_met.join(", ")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="eyebrow mb-2">No submission</div>
          <div className="text-muted">{e.not_submitted.map((s) => s.student_name).join(", ") || "None"}</div>
        </div>
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------- submissions

type Filter = "all" | "review" | "misconception" | "ready";

function SubmissionsTab({ a }: { a: AssignmentDetail }) {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const q = useQuery({ queryKey: ["submissions", String(a.id)], queryFn: () => api<SubmissionRow[]>(`/api/professor/assignments/${a.id}/submissions`) });
  const publish = useMutation({
    mutationFn: () => api<{ published: number[]; blocked: { reasons: string[] }[] }>(`/api/professor/assignments/${a.id}/publish`, { method: "POST", json: {} }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["submissions", String(a.id)] });
      qc.invalidateQueries({ queryKey: ["assignment", String(a.id)] });
    },
  });
  const rows = useMemo(() => {
    const all = q.data ?? [];
    return all.filter((r) => {
      if (search && !r.student.name.toLowerCase().includes(search.toLowerCase())) return false;
      if (filter === "review") return r.needs_review;
      if (filter === "misconception") return r.misconceptions.length > 0;
      if (filter === "ready") return r.grade_status === "reviewed";
      return true;
    });
  }, [q.data, filter, search]);
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const crits = a.criteria;

  return (
    <div className="pt-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex flex-wrap gap-1">
          {([["all", "All"], ["review", "Needs review"], ["misconception", "Misconception evidence"], ["ready", "Reviewed"]] as [Filter, string][]).map(([f, l]) => (
            <button key={f} onClick={() => setFilter(f)}
              className={cx("h-7 px-2.5 rounded text-[13.5px]", filter === f ? "bg-raised text-ink" : "text-muted hover:text-ink")}>
              {l}
            </button>
          ))}
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Find a student"
            className="ml-2 h-7 w-44 bg-surface border border-line rounded px-2 text-[13.5px] placeholder:text-faint" />
        </div>
        <Button onClick={() => publish.mutate()} disabled={publish.isPending}>Publish reviewed grades</Button>
      </div>
      {publish.data && (
        <div className="mb-4">
          <Callout tone={publish.data.published.length ? "accent" : "amber"} title={`${publish.data.published.length} grades published`}>
            {publish.data.blocked.length} held back: a grade is only published once every criterion rests on tests or your own decision.
            AI suggestions alone never release a grade.
          </Callout>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-[14px] min-w-[760px]">
          <thead>
            <tr className="text-left text-faint text-2xs uppercase tracking-[0.1em] border-b border-line">
              <th className="font-medium py-2">Student</th>
              {crits.map((c) => <th key={c.id} className="font-medium py-2 px-2" title={c.title}>{c.code}</th>)}
              <th className="font-medium py-2 text-right pr-4">Total</th>
              <th className="font-medium py-2">Flags</th>
              <th className="font-medium py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.id} className="hover:bg-surface/50">
                <td className="py-2.5 pr-3">
                  <Link to={`/p/submissions/${r.id}`} className="text-ink hover:text-accent-ink">{r.student.name}</Link>
                </td>
                {r.criteria.map((c) => (
                  <td key={c.criterion_id} className="py-2.5 px-2" title={`${c.code}: ${c.judgment ?? "no evidence"} (${c.source ?? "—"})`}>
                    <span className="inline-flex items-center gap-1">
                      <JudgmentMark judgment={c.judgment} compact />
                      {c.source === "ai" && c.judgment !== "ai_unavailable" && <span className="text-2xs text-amber">AI</span>}
                      {c.source === "baseline" && <span className="text-2xs text-amber">Rule</span>}
                      {c.source === "professor" && <span className="text-2xs text-accent-ink">You</span>}
                    </span>
                  </td>
                ))}
                <td className="py-2.5 text-right pr-4 num">
                  {r.total === null ? <span className="text-faint">—</span> : (
                    <span className={r.includes_unconfirmed_ai ? "text-amber" : ""} title={r.includes_unconfirmed_ai ? "Includes unconfirmed AI suggestions" : ""}>
                      {r.total}<span className="text-faint">/{r.max_total}</span>
                    </span>
                  )}
                </td>
                <td className="py-2.5">
                  <span className="flex flex-wrap gap-1">
                    {r.needs_review && <Tag tone="amber">Review</Tag>}
                    {r.misconceptions.map((m) => <Tag key={m} tone="brick">{m.replace("MC-", "")}</Tag>)}
                  </span>
                </td>
                <td className="py-2.5 text-muted text-[13.5px]">{r.grade_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-4 text-2xs text-faint mt-3">
        <span>{rows.length} shown</span><span>·</span>
        <span><JudgmentMark judgment="met" /></span><span><JudgmentMark judgment="partial" /></span>
        <span><JudgmentMark judgment="not_met" /></span><span><JudgmentMark judgment="ai_unavailable" /></span>
        <span className="text-amber">AI / Rule</span><span>= unconfirmed machine reading</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- rubric

function RubricTab({ a }: { a: AssignmentDetail }) {
  const [showSolution, setShowSolution] = useState(false);
  return (
    <div className="pt-2">
      <Section title="Task">
        <p className="whitespace-pre-line max-w-prose text-muted">{a.prompt}</p>
        <p className="mt-3 max-w-prose text-muted"><span className="text-ink">Written explanation. </span>{a.explanation_prompt}</p>
        <p className="mt-3 max-w-prose text-[13.5px] text-faint"><span className="text-muted">AI policy. </span>{a.ai_policy}</p>
      </Section>
      <Section title="Rubric" aside={`${a.criteria.reduce((s, c) => s + c.max_points, 0)} points`}>
        <table className="w-full text-[14px]">
          <tbody className="divide-y divide-line">
            {a.criteria.map((c) => (
              <tr key={c.id}>
                <td className="py-3 pr-4 font-mono text-[13px] text-accent-ink w-10 align-top">{c.code}</td>
                <td className="py-3 pr-4 align-top">
                  <div className="text-ink">{c.title}</div>
                  <div className="text-muted text-[13.5px]">{c.description}</div>
                </td>
                <td className="py-3 pr-4 align-top text-muted whitespace-nowrap">
                  {c.method === "tests" ? "Scored by tests" : "AI suggests, you confirm"}
                </td>
                <td className="py-3 pr-4 align-top text-faint font-mono text-[11px]">{c.objective_code}</td>
                <td className="py-3 align-top text-right num">{c.max_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <Section title="Tests" aside="Probes link a failing test to a misconception hypothesis">
        <table className="w-full text-[14px]">
          <tbody className="divide-y divide-line">
            {a.tests.map((t) => {
              const crit = a.criteria.find((c) => c.id === t.criterion_id);
              return (
                <tr key={t.id}>
                  <td className="py-2.5 pr-4 font-mono text-[13px]">{t.name}</td>
                  <td className="py-2.5 pr-4 text-faint font-mono text-[11px]">{crit?.code}</td>
                  <td className="py-2.5 pr-4">{t.hidden && <Tag>Hidden from students</Tag>}</td>
                  <td className="py-2.5 text-[13px] text-muted">
                    {t.probes.map((p) => `${p.misconception.replace("MC-", "")} on ${p.on === "error" ? (p.error_types ?? []).join("/") : "wrong value"}`).join(" · ")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Section>
      <Section title="Misconceptions to watch for" aside="Hypotheses. ATHAR checks for them, never assumes them">
        <ul className="space-y-3">
          {a.misconceptions.map((m) => (
            <li key={m.code} className="grid grid-cols-[150px_1fr] gap-4 text-[14px]">
              <span className="font-mono text-[11.5px] text-faint pt-0.5">{m.code}</span>
              <div><div className="text-ink">{m.title}</div><div className="text-muted">{m.description}</div></div>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Reference solution" aside={<button className="link" onClick={() => setShowSolution((v) => !v)}>{showSolution ? "Hide" : "Show"}</button>}>
        {showSolution ? <CodeBlock code={a.reference_solution} /> : <p className="text-[13.5px] text-faint">Never shown to students.</p>}
      </Section>
    </div>
  );
}
