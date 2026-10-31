import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { OverviewTab } from "./Overview";
import { criterionLabel, misconceptionLabel } from "../../lib/labels";
import type { AssignmentDetail, GradingRun, SubmissionRow } from "../../lib/types";
import {
  Button, CONDITIONS, Callout, CodeBlock, Crumb, Empty, ErrorState, JudgmentMark, KIND, Loading, Meter, PageHeader,
  Section, Tag, cx, fmtDate,
} from "../../components/ui";

const TABS = [
  { id: "overview", label: "Who needs attention" },
  { id: "submissions", label: "All submissions" },
  { id: "rubric", label: "Rubric & tests" },
] as const;

export function AssignmentPage() {
  const { assignmentId } = useParams();
  const [params, setParams] = useSearchParams();
  const raw = params.get("tab") ?? "overview";
  const tab = raw === "insights" || raw === "plan" ? "overview" : raw;
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
      {tab === "overview" && <OverviewTab a={a} />}
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
      {!running && live?.status === "done" && live.ai_status === "replayed" && (
        <Callout tone="amber" title="Recorded AI readings (replay)">
          These explanation readings are the stored outputs of an earlier live run ({live.ai_provider}). They were replayed without calling a model,
          so this isn't fresh inference. Tests were re-run in the sandbox.
        </Callout>
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

// ---------------------------------------------------------------- submissions

type Filter = "all" | "review" | "tests_failed" | "flagged" | "awaiting" | "reviewed";
const FILTERS: [Filter, string][] = [["all", "All"], ["review", "Needs review"], ["tests_failed", "Tests failed"], ["flagged", "Flagged"], ["awaiting", "Awaiting your decision"], ["reviewed", "Reviewed"]];
const PAGE = 20;

function matches(r: SubmissionRow, f: Filter) {
  if (f === "review") return r.needs_review;
  if (f === "tests_failed") return r.criteria.some((c) => c.source === "tests" && c.judgment !== "met");
  if (f === "flagged") return r.misconceptions.length > 0;
  if (f === "awaiting") return r.includes_unconfirmed_ai || r.criteria.some((c) => c.judgment === "ai_unavailable" || c.judgment === "ai_failed");
  if (f === "reviewed") return r.grade_status === "reviewed" || r.grade_status === "published";
  return true;
}

function SubmissionsTab({ a }: { a: AssignmentDetail }) {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const filter = (params.get("f") as Filter) || "all";
  const search = params.get("q") ?? "";
  const sort = params.get("sort") ?? "name";
  const page = Math.max(1, Number(params.get("page") ?? 1));
  const set = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    next.set("tab", "submissions");
    setParams(next, { replace: true });
  };
  useEffect(() => {  // remember this exact list view for "Back to all submissions"
    try { sessionStorage.setItem("athar.submissionsList", `/p/assignments/${a.id}?${params.toString()}`); } catch { /* ignore */ }
  }, [params, a.id]);
  const q = useQuery({ queryKey: ["submissions", String(a.id)], queryFn: () => api<SubmissionRow[]>(`/api/professor/assignments/${a.id}/submissions`) });
  const publish = useMutation({
    mutationFn: () => api<{ published: number[]; blocked: { reasons: string[] }[] }>(`/api/professor/assignments/${a.id}/publish`, { method: "POST", json: {} }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["submissions", String(a.id)] }); qc.invalidateQueries({ queryKey: ["assignment", String(a.id)] }); },
  });
  const all = q.data ?? [];
  const rows = useMemo(() => {
    const r = all.filter((x) => matches(x, filter) && (!search || x.student.name.toLowerCase().includes(search.toLowerCase())));
    const by: Record<string, (x: SubmissionRow) => number | string> = {
      name: (x) => x.student.name, score: (x) => -(x.total ?? -1), status: (x) => (x.needs_review ? 0 : 1) + x.student.name,
    };
    return [...r].sort((p, q2) => { const A = by[sort]?.(p) ?? 0, B = by[sort]?.(q2) ?? 0; return A < B ? -1 : A > B ? 1 : 0; });
  }, [all, filter, search, sort]);
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const shown = rows.slice((Math.min(page, pages) - 1) * PAGE, Math.min(page, pages) * PAGE);
  const crits = a.criteria;

  return (
    <div className="pt-6">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input value={search} onChange={(e) => set({ q: e.target.value, page: "" })} placeholder="Search students" aria-label="Search students"
          className="h-10 w-full sm:w-64 bg-surface border border-line-strong rounded px-3 text-[15px] placeholder:text-faint" />
        <label className="text-[14px] text-muted flex items-center gap-2">Sort
          <select value={sort} onChange={(e) => set({ sort: e.target.value })} className="h-10 bg-surface border border-line-strong rounded px-2 text-ink">
            <option value="name">Name</option><option value="status">Needs review first</option><option value="score">Score</option>
          </select>
        </label>
        <Button className="sm:ml-auto" onClick={() => publish.mutate()} disabled={publish.isPending}>Release reviewed feedback</Button>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-4" role="group" aria-label="Filter submissions">
        {FILTERS.map(([f, l]) => (
          <button key={f} onClick={() => set({ f: f === "all" ? "" : f, page: "" })} aria-pressed={filter === f}
            className={cx("h-9 px-3 rounded-full text-[14px] border", filter === f ? "border-accent-strong bg-accent-wash text-ink" : "border-line text-muted hover:text-ink")}>
            {l} <span className="text-faint num">{all.filter((x) => matches(x, f)).length}</span>
          </button>
        ))}
      </div>
      {publish.data && (
        <div className="mb-4"><Callout tone={publish.data.published.length ? "accent" : "amber"} title={`${publish.data.published.length} released`}>
          {publish.data.blocked.length} held back until every criterion rests on tests or your decision.</Callout></div>
      )}
      {shown.length === 0 ? <Empty title="No submissions match">Try another filter or clear the search.</Empty> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[14.5px] min-w-[720px]">
            <thead>
              <tr className="text-left text-faint text-[13px] border-b border-line">
                <th className="font-medium py-2.5">Student</th>
                {crits.map((c) => <th key={c.id} className="font-medium py-2.5 px-2 max-w-[110px]" title={`${c.code}: ${c.title}`}>{criterionLabel(c.code)}</th>)}
                <th className="font-medium py-2.5 text-right pr-4">Score</th>
                <th className="font-medium py-2.5">Flags</th>
                <th className="sr-only">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {shown.map((r) => (
                <tr key={r.id} className="hover:bg-surface/60">
                  <td className="py-3 pr-3"><Link to={`/p/submissions/${r.id}`} className="text-ink hover:text-accent-ink">{r.student.name}</Link></td>
                  {r.criteria.map((c) => (
                    <td key={c.criterion_id} className="py-3 px-2" title={`${criterionLabel(c.code)}: ${c.judgment ?? "no evidence"} (${c.source ?? "—"})`}>
                      <span className="inline-flex items-center gap-1.5"><JudgmentMark judgment={c.judgment} compact />
                        {(c.source === "ai" || c.source === "baseline") && c.judgment !== "ai_unavailable" && <span className="text-[12px] text-amber">suggested</span>}
                        {c.source === "professor" && <span className="text-[12px] text-accent-ink">you</span>}</span>
                    </td>
                  ))}
                  <td className="py-3 text-right pr-4 num">{r.total === null ? <span className="text-faint">—</span> : <>{r.total}<span className="text-faint">/{r.max_total}</span></>}</td>
                  <td className="py-3"><span className="flex flex-wrap gap-1">{[...new Set(r.misconceptions)].slice(0, 2).map((m) => <Tag key={m} tone="amber" title={`${m}: flagged, not confirmed`}>{misconceptionLabel(m)}</Tag>)}</span></td>
                  <td className="py-3 text-right"><Link to={`/p/submissions/${r.id}`} className="link text-[14px]">Review →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-[14px] text-muted">
        <span className="num">{rows.length} of {all.length} submissions</span>
        {pages > 1 && (
          <span className="flex items-center gap-2" aria-label="Pages">
            <Button variant="ghost" disabled={page <= 1} onClick={() => set({ page: String(page - 1) })}>← Previous</Button>
            <span className="num">Page {Math.min(page, pages)} of {pages}</span>
            <Button variant="ghost" disabled={page >= pages} onClick={() => set({ page: String(page + 1) })}>Next →</Button>
          </span>
        )}
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
