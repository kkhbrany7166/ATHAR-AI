// Assignment overview: "Who needs my attention, and why?"
// One list of student groups (from the deterministic diagnosis), each with its evidence type, proposed action,
// activity status and a drill-down. Replaces the separate Insights and Who-needs-what lists.
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { misconceptionLabel } from "../../lib/labels";
import type { AssignmentDetail, Insight, InsightEvidence, Plan, PlanGroup } from "../../lib/types";
import { EvidenceTag } from "../../components/Evidence";
import { Button, Callout, ErrorState, Loading, cx } from "../../components/ui";

interface CourseIv { id: number; status: string; kind: string; misconception_code: string; assignment_id: number; targets: number; delivered: number; verified: number }

const ORDER = ["concept_gap", "reasoning_gap", "execution_error", "reasoning_unconfirmed", "no_submission", "demonstrated"];
const KIND_FOR: Record<string, string> = { concept_gap: "concept_practice", reasoning_gap: "explain_reasoning", reasoning_unconfirmed: "explain_reasoning", execution_error: "debugging" };
const WHY: Record<string, string> = {
  concept_gap: "A smallest-input test failed in the way this misconception predicts. Deterministic evidence.",
  reasoning_gap: "All tests pass, but the AI read the explanation as holding a stopping-condition misconception. A suggestion to check, not a diagnosis.",
  execution_error: "The code didn't run, so the tests couldn't show anything about recursion yet.",
  reasoning_unconfirmed: "All tests pass, but the explanation was too thin, unclear or unread to confirm understanding.",
  no_submission: "Nothing to look at. ATHAR won't guess.",
  demonstrated: "Tests pass and the AI read the reasoning as sound. Not verified by an independent check.",
};

function evidenceKinds(g: PlanGroup): ("test" | "ai")[] {
  if (g.category === "concept_gap" || g.category === "execution_error") return ["test"];
  if (g.category === "reasoning_gap" || g.category === "demonstrated") return ["test", "ai"];
  if (g.category === "reasoning_unconfirmed") return ["test"];
  return [];
}

export function OverviewTab({ a }: { a: AssignmentDetail }) {
  const plan = useQuery({ queryKey: ["plan", a.id], queryFn: () => api<Plan>(`/api/professor/assignments/${a.id}/plan`) });
  const ins = useQuery({ queryKey: ["insights", String(a.id)], queryFn: () => api<{ insights: Insight[] }>(`/api/professor/assignments/${a.id}/insights`) });
  const ivs = useQuery({ queryKey: ["course", String(a.course_id), "interventions"], queryFn: () => api<CourseIv[]>(`/api/professor/courses/${a.course_id}/interventions`) });
  if (plan.isLoading || ins.isLoading) return <Loading label="Reading the evidence" />;
  if (plan.error) return <ErrorState error={plan.error} />;
  const groups = [...(plan.data?.groups ?? [])].sort((x, y) => ORDER.indexOf(x.category) - ORDER.indexOf(y.category));
  const count = (cat: string) => groups.filter((g) => g.category === cat).reduce((n, g) => n + g.students.length, 0);
  const insightFor = (g: PlanGroup) => (ins.data?.insights ?? []).find((i) => i.kind === "misconception" &&
    (g.category === "concept_gap" ? i.misconception_code === g.misconception_code : g.category === "reasoning_gap" ? i.misconception_code === "MC-STOP-IMPLICIT" : false));
  const ivFor = (g: PlanGroup) => (ivs.data ?? []).find((iv) => iv.assignment_id === a.id && iv.kind === KIND_FOR[g.category] &&
    (g.category !== "concept_gap" || iv.misconception_code === g.misconception_code) && iv.status !== "rejected");
  const readerAI = plan.data?.reader_status === "used";
  const submitted = groups.filter((g) => g.category !== "no_submission").reduce((n, g) => n + g.students.length, 0);

  return (
    <div className="pt-6">
      {/* The question, answered in one line each */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 border-y border-line divide-y sm:divide-y-0 lg:divide-x divide-line">
        <Fig n={count("concept_gap")} of={submitted} label="fail tests in a way that points to a base-case gap" kind="test" />
        <Fig n={count("reasoning_gap")} of={submitted} label="pass every test, but the explanation was flagged" kind="ai" />
        <Fig n={count("execution_error") + count("reasoning_unconfirmed")} of={submitted} label="need a closer look: code didn't run, or reasoning unclear" />
        <Fig n={count("demonstrated")} of={submitted} label="pass and read as sound: no action proposed" />
      </div>

      {readerAI && (
        <div className="mt-6">
          <p className="text-[14.5px] text-amber border-l-2 border-amber pl-3">AI flags are leads, not diagnoses. On this class the AI over-flags, so check the quoted evidence before acting.</p>
        </div>
      )}

      <h2 className="font-serif text-[26px] mt-10 mb-4">Review queue</h2>
      <ol className="divide-y divide-line border-y border-line">
        {groups.map((g) => <GroupRow key={g.category + g.misconception_code} g={g} a={a} insight={insightFor(g)} iv={ivFor(g)} kinds={evidenceKinds(g)} readerAI={readerAI} />)}
      </ol>
    </div>
  );
}

function Fig({ n, of, label, kind }: { n: number; of: number; label: string; kind?: "test" | "ai" }) {
  return (
    <div className="py-5 px-1 lg:px-5 lg:first:pl-0">
      <div className="flex items-baseline gap-2"><span className="font-serif text-[34px] leading-none num">{n}</span><span className="text-faint text-[13px] num">of {of}</span></div>
      <div className="text-[14px] text-muted mt-2 leading-snug">{label}</div>
      {kind && <div className="mt-2"><EvidenceTag kind={kind} /></div>}
    </div>
  );
}

const STATUS: Record<string, string> = { draft: "Draft waiting for your approval", approved: "Approved", active: "Delivered", completed: "Closed" };

function GroupRow({ g, a, insight, iv, kinds, readerAI }: { g: PlanGroup; a: AssignmentDetail; insight?: Insight; iv?: CourseIv; kinds: ("test" | "ai")[]; readerAI: boolean }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const available = g.students.filter((s) => !s.in_intervention);
  const draft = useMutation({
    mutationFn: () => api<{ id: number }>(`/api/professor/assignments/${a.id}/plan/draft`, {
      method: "POST", json: { category: g.category, misconception_code: g.misconception_code, student_ids: available.map((s) => s.student_id) },
    }),
    onSuccess: (r) => navigate(`/p/interventions/${r.id}`),
  });
  const quiet = g.category === "demonstrated" || g.category === "no_submission";
  const first = g.students.find((s) => s.evidence.length) ?? g.students[0];
  const preview = first && first.evidence[0] ? `${first.name}: ${first.evidence[0]}` : "";
  const ev = insight?.evidence as InsightEvidence | undefined;
  const base = g.label.split(" · ")[0];
  const title = g.category === "concept_gap" && g.misconception_code ? `${base}: ${misconceptionLabel(g.misconception_code).toLowerCase()}` : base;
  const why = g.category === "concept_gap" && g.misconception_code === "MC-NO-PROGRESS"
    ? "Typical tests ran into RecursionError: the recursive call never reaches the base case. Deterministic evidence."
    : g.category === "concept_gap" && g.misconception_code === "MC-BASE-VALUE"
      ? "A smallest-input test returned the wrong value. Deterministic evidence."
      : WHY[g.category];

  return (
    <li className={cx("py-5", quiet && "opacity-90")}>
      <div className="grid md:grid-cols-[72px_minmax(0,1fr)_auto] gap-x-6 gap-y-3 items-start">
        <div className={cx("font-serif text-[30px] leading-none num", quiet ? "text-muted" : "text-ink")}>{g.students.length}</div>
        <div className="min-w-0">
          <div className="text-[16.5px] text-ink">{title}</div>
          {preview && <p className="text-[15px] text-muted mt-1.5 max-w-prose truncate" title={preview}>{preview}</p>}
          <div className="flex flex-wrap items-center gap-2 mt-2.5">
            {kinds.map((k) => <EvidenceTag key={k} kind={k === "ai" && !readerAI ? "rules" : k} />)}
            {!quiet && <span className="text-[14px] text-faint">Suggested: <span className="text-muted">{g.action_label.toLowerCase()}</span></span>}
          </div>
        </div>
        <div className="flex md:flex-col md:items-end gap-2">
          {iv ? (
            <Link to={`/p/interventions/${iv.id}`} className="text-[14px] text-accent-ink hover:underline underline-offset-4 text-right">
              {STATUS[iv.status] ?? iv.status}{iv.status === "active" ? ` · ${iv.verified}/${iv.delivered} checked` : ""} →
            </Link>
          ) : g.draftable && available.length > 0 ? (
            <Button onClick={() => draft.mutate()} disabled={draft.isPending}>{draft.isPending ? "Drafting…" : `Plan for ${available.length}`}</Button>
          ) : null}
          <button onClick={() => setOpen((x) => !x)} aria-expanded={open} className="text-[13.5px] text-faint hover:text-ink">
            {open ? "Hide" : "See the evidence"}
          </button>
        </div>
      </div>
      {draft.error && <div className="mt-3 md:ml-[96px]"><Callout tone="brick">{(draft.error as Error).message}</Callout></div>}
      {open && <p className="mt-3 md:ml-[96px] text-[14.5px] text-muted max-w-prose">{why}</p>}
      {open && (
        <div className="mt-4 md:ml-[96px] grid lg:grid-cols-[minmax(0,1fr)_280px] gap-x-10 gap-y-4">
          <ul className="space-y-2.5 text-[14px]">
            {g.students.slice(0, 8).map((s) => (
              <li key={s.student_id} className="grid sm:grid-cols-[190px_minmax(0,1fr)] gap-x-4">
                {s.submission_id ? <Link to={`/p/submissions/${s.submission_id}`} className="text-ink hover:text-accent-ink truncate">{s.name}</Link> : <span className="text-ink">{s.name}</span>}
                <span className="text-muted">{s.evidence.join(" · ")}</span>
              </li>
            ))}
            {g.students.length > 8 && <li className="text-faint text-[13.5px]">and {g.students.length - 8} more{insight ? ", all listed on the evidence page" : ""}.</li>}
          </ul>
          {insight && ev && (
            <div className="text-[13.5px] border-l border-line pl-5">
              <div className="text-ink">How this group was found</div>
              <ul className="text-muted mt-1.5 space-y-1">
                <li>{ev.counts.tests_only + ev.counts.both} flagged by failing tests</li>
                <li>{ev.counts.explanation_only + ev.counts.both} flagged by the AI reading of the explanation</li>
                {ev.contradictions.length > 0 && <li className="text-amber">{ev.contradictions.length} kinds of disagreeing evidence</li>}
              </ul>
              <Link to={`/p/insights/${insight.id}`} className="link inline-block mt-3">Open the full evidence →</Link>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
