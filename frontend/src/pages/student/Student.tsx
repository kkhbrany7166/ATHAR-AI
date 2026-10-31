import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useSession } from "../../lib/session";
import type { StudentAssignment, StudentHome } from "../../lib/types";
import { CONDITIONS, Callout, CodeBlock, Crumb, ErrorState, JudgmentMark, KIND, Loading, PageHeader, Section, Tag, fmtDate } from "../../components/ui";

const TASK_OUTCOME: Record<string, string> = {
  demonstrated: "Shown on the check", still_developing: "Still developing", insufficient_evidence: "With your professor",
};

const MY_STATUS: Record<string, { label: string; tone: "neutral" | "accent" | "amber" }> = {
  not_submitted: { label: "Not submitted", tone: "amber" },
  submitted: { label: "Submitted, awaiting feedback", tone: "neutral" },
  feedback_ready: { label: "Feedback ready", tone: "accent" },
};

export function StudentHomePage() {
  const { user } = useSession();
  const q = useQuery({ queryKey: ["student-home"], queryFn: () => api<StudentHome>("/api/student/home") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const first = user?.name.split(" ")[0];

  return (
    <>
      <PageHeader eyebrow="My learning" title={`Welcome back, ${first}.`}>
        Some activities are practice, where asking for help is the point. Others are checks, where you show what you can do on your own.
        Each one tells you which it is.
      </PageHeader>
      {q.data!.tasks.length > 0 && (
        <Section title="Picked for you" aside="From your professor">
          <ul className="space-y-3">
            {q.data!.tasks.map((t) => (
              <li key={t.id}>
                <Link to={`/s/tasks/${t.id}`} className="group block border border-line-strong rounded-lg px-6 py-5 hover:border-accent-strong hover:bg-surface transition-colors">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-serif text-[21px] text-ink">{t.title}</div>
                      <p className="text-muted text-[14.5px] mt-1 max-w-prose">
                        A short explanation, some practice with hints, and a new problem to try on your own. About twenty minutes.
                      </p>
                    </div>
                    <Tag tone={t.outcome === "demonstrated" ? "accent" : t.status === "assigned" ? "amber" : "neutral"}>
                      {t.outcome ? TASK_OUTCOME[t.outcome] : t.status === "assigned" ? "New" : "In progress"}
                    </Tag>
                  </div>
                  <div className="text-[14px] text-accent-ink mt-3 group-hover:underline underline-offset-4">
                    {t.status === "assigned" ? "Start" : t.outcome ? "Review" : "Continue"} →
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {q.data!.courses.map((c) => (
        <Section key={c.id} title={<><span className="text-faint mr-2">{c.code}</span>{c.title}</>} aside={c.professor}>
          <ul className="divide-y divide-line">
            {c.assignments.map((a) => (
              <li key={a.id}>
                <Link to={`/s/assignments/${a.id}`} className="flex flex-wrap items-center justify-between gap-3 py-4 group">
                  <div>
                    <div className="text-ink group-hover:text-accent-ink transition-colors">{a.title}</div>
                    <div className="text-[13.5px] text-muted mt-0.5">
                      {KIND[a.kind]} · {CONDITIONS[a.conditions]?.label} · due {fmtDate(a.due_at)}
                    </div>
                  </div>
                  <Tag tone={MY_STATUS[a.my_status]?.tone}>{MY_STATUS[a.my_status]?.label ?? a.my_status}</Tag>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      ))}
    </>
  );
}

export function StudentAssignmentPage() {
  const { assignmentId } = useParams();
  const q = useQuery({ queryKey: ["student-assignment", assignmentId], queryFn: () => api<StudentAssignment>(`/api/student/assignments/${assignmentId}`) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const { assignment: a, submissions } = q.data!;
  const latest = submissions[submissions.length - 1];

  return (
    <>
      <div className="text-[13px] text-faint mb-5"><Crumb to="/s">My learning</Crumb> / {a.course_code}</div>
      <PageHeader eyebrow={`${a.course_code} · due ${fmtDate(a.due_at)}`} title={a.title}>
        <span className="flex flex-wrap gap-1.5 mt-1"><Tag>{KIND[a.kind]}</Tag><Tag>{CONDITIONS[a.conditions]?.label}</Tag></span>
      </PageHeader>
      <Callout title={CONDITIONS[a.conditions]?.label}>{CONDITIONS[a.conditions]?.help} {a.ai_policy}</Callout>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-x-12">
        <div>
          <Section title="The task">
            <p className="whitespace-pre-line text-muted max-w-prose">{a.prompt}</p>
            <p className="text-muted max-w-prose mt-3"><span className="text-ink">Explain your reasoning. </span>{a.explanation_prompt}</p>
          </Section>
          {latest && (
            <>
              <Section title="Your explanation" aside={`Submitted ${fmtDate(latest.submitted_at)}`}>
                <p className="font-serif text-[16px] leading-[1.7] max-w-prose">{latest.explanation || <span className="text-faint">No explanation.</span>}</p>
              </Section>
              <Section title="Your code"><CodeBlock code={latest.code} /></Section>
            </>
          )}
        </div>
        <aside className="lg:pt-6">
          <div className="eyebrow mb-3">Feedback</div>
          {!latest ? <p className="text-muted text-[14px]">You haven't submitted this one.</p>
            : !latest.feedback ? (
              <p className="text-muted text-[14px]">
                Your professor is reviewing submissions. Feedback appears here once they've confirmed it. ATHAR never releases a grade on its own.
              </p>
            ) : (
              <div className="space-y-4 text-[14px]">
                <div className="font-serif text-[28px] num">{latest.feedback.total}<span className="text-faint text-[17px]">/{latest.feedback.max_total}</span></div>
                {latest.feedback.criteria.map((c) => (
                  <div key={c.code}>
                    <div className="flex justify-between gap-2"><span className="text-ink">{c.title}</span><span className="num text-muted">{c.points ?? "—"}/{c.max_points}</span></div>
                    {c.judgment && <JudgmentMark judgment={c.judgment as never} />}
                    {c.comment && <p className="text-muted mt-1">{c.comment}</p>}
                  </div>
                ))}
                <div>
                  <div className="eyebrow mb-1.5">Visible tests</div>
                  <ul className="space-y-1 font-mono text-[13px]">
                    {latest.feedback.tests.map((t) => <li key={t.name} className={t.passed ? "text-accent-ink" : "text-brick"}>{t.passed ? "✓" : "✗"} {t.name}</li>)}
                  </ul>
                </div>
              </div>
            )}
          <div className="mt-8">
            <div className="eyebrow mb-2">Rubric</div>
            <ul className="space-y-2 text-[13.5px] text-muted">
              {a.criteria.map((c) => <li key={c.code}><span className="text-ink">{c.title}</span> · {c.max_points} pts</li>)}
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}
