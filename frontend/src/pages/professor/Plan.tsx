import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Plan, PlanGroup } from "../../lib/types";
import { Button, Callout, Empty, ErrorState, Loading, Section, Tag, cx } from "../../components/ui";

const TONE: Record<string, string> = {
  concept_gap: "border-brick/60", reasoning_gap: "border-amber/70", execution_error: "border-slate/60",
  reasoning_unconfirmed: "border-line-strong", no_submission: "border-line-strong", demonstrated: "border-accent-strong",
};

export function PlanTab({ assignmentId }: { assignmentId: number }) {
  const q = useQuery({ queryKey: ["plan", assignmentId], queryFn: () => api<Plan>(`/api/professor/assignments/${assignmentId}/plan`) });
  if (q.isLoading) return <Loading label="Reading the evidence" />;
  if (q.error) return <ErrorState error={q.error} />;
  const p = q.data!;
  if (!p.groups.length) return <Empty title="No evidence yet">Prepare grading evidence first.</Empty>;
  const readerLabel = p.reader_status === "used" ? `AI (${p.reader})` : p.reader_status === "baseline" ? `the rule-based reader ${p.reader} (not AI)` : "no reader";

  return (
    <div className="pt-2">
      <Section title="Who needs what" aside={`Explanations read by ${readerLabel}`}>
        <p className="text-muted text-[14px] max-w-prose mb-5">
          Every student is placed in exactly one group by fixed rules over their tests and their explanation reading. Different difficulties get
          different help: a debugging exercise won't fix a misunderstanding, and re-teaching recursion won't help someone whose code just didn't run.
          You choose which proposals to draft; nothing reaches students until you approve.
        </p>
        <div className="space-y-4">
          {p.groups.map((g) => <Group key={g.category + g.misconception_code} g={g} assignmentId={assignmentId} />)}
        </div>
        <p className="text-[12.5px] text-faint mt-5">Diagnosis rules: backend/athar/{p.rules.replace("athar/", "")}</p>
      </Section>
    </div>
  );
}

function Group({ g, assignmentId }: { g: PlanGroup; assignmentId: number }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const available = g.students.filter((s) => !s.in_intervention);
  const existing = g.students.find((s) => s.in_intervention)?.in_intervention;
  const draft = useMutation({
    mutationFn: () => api<{ id: number }>(`/api/professor/assignments/${assignmentId}/plan/draft`, {
      method: "POST", json: { category: g.category, misconception_code: g.misconception_code, student_ids: available.map((s) => s.student_id) },
    }),
    onSuccess: (iv) => navigate(`/p/interventions/${iv.id}`),
  });
  return (
    <div className={cx("border-l-2 pl-5 py-1", TONE[g.category] ?? "border-line")}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-serif text-[24px] num leading-none">{g.students.length}</span>
            <span className="text-ink text-[15px]">{g.label}</span>
          </div>
          <div className="text-[14px] mt-1.5">
            <span className="text-muted">Proposed: </span><span className="text-ink">{g.action_label}</span>
            <span className="text-faint">. {g.action_why}</span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          {existing ? (
            <Link to={`/p/interventions/${existing}`} className="link text-[14px]">Open intervention</Link>
          ) : g.draftable ? (
            <Button disabled={draft.isPending || !available.length} onClick={() => draft.mutate()}>
              {draft.isPending ? "Drafting…" : `Draft for ${available.length}`}
            </Button>
          ) : <Tag>{g.action === "none" ? "No action needed" : "Handle personally"}</Tag>}
        </div>
      </div>
      {draft.error && <div className="mt-2"><Callout tone="brick">{(draft.error as Error).message}</Callout></div>}
      <button className="text-[13px] text-faint hover:text-ink mt-2" onClick={() => setOpen((x) => !x)}>
        {open ? "Hide" : "Show"} students and evidence
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5 text-[13.5px] max-h-80 overflow-y-auto pr-2">
          {g.students.map((s) => (
            <li key={s.student_id} className="grid sm:grid-cols-[200px_1fr] gap-x-4">
              {s.submission_id ? <Link to={`/p/submissions/${s.submission_id}`} className="text-ink hover:text-accent-ink truncate">{s.name}</Link>
                : <span className="text-ink truncate">{s.name}</span>}
              <span className="text-faint truncate" title={s.evidence.join(" · ")}>{s.evidence.join(" · ")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
