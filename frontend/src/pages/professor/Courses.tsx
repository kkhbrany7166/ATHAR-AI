import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { CourseDetail, CourseSummary, Plan } from "../../lib/types";
import { misconceptionLabel } from "../../lib/labels";
import { EvidenceTag } from "../../components/Evidence";
import { Crumb, Empty, ErrorState, Loading, PageHeader, Section, SynthTag, fmtDate } from "../../components/ui";
import { useParams } from "react-router-dom";

export function Courses() {
  const q = useQuery({ queryKey: ["prof-courses"], queryFn: () => api<CourseSummary[]>("/api/professor/courses") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  return (
    <>
      <PageHeader eyebrow="Your teaching" title="Courses" />
      {q.data!.length === 0 ? <Empty title="No courses yet" /> : (
        <div className="divide-y divide-line border-y border-line">
          {q.data!.map((c) => (
            <Link key={c.id} to={`/p/courses/${c.id}`} className="flex items-center justify-between py-4 px-1 hover:bg-surface/60">
              <div>
                <div className="text-[15px]"><span className="text-faint mr-2">{c.code}</span>{c.title}</div>
                <div className="text-[13.5px] text-muted mt-0.5 num">{c.term} · {c.student_count} students · {c.assignment_count} {c.assignment_count === 1 ? "assignment" : "assignments"}</div>
              </div>
              {c.is_synthetic && <SynthTag />}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

export function CourseOverview() {
  const { courseId } = useParams();
  const q = useQuery({ queryKey: ["course", courseId], queryFn: () => api<CourseDetail>(`/api/professor/courses/${courseId}`) });
  const main = q.data?.assignments.find((a) => !a.targeted && a.latest_run?.status === "done");
  const plan = useQuery({ queryKey: ["plan", main?.id], queryFn: () => api<Plan>(`/api/professor/assignments/${main!.id}/plan`), enabled: !!main });
  const ivs = useQuery({
    queryKey: ["course", courseId, "interventions"],
    queryFn: () => api<{ id: number; title: string; status: string; kind: string; targets: number; delivered: number; verified: number }[]>(`/api/professor/courses/${courseId}/interventions`),
  });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const c = q.data!;
  const actionable = (plan.data?.groups ?? []).filter((g) => g.draftable && g.students.some((s) => !s.in_intervention));
  const waiting = (ivs.data ?? []).filter((iv) => iv.status === "draft");
  const results = (ivs.data ?? []).filter((iv) => iv.status === "active");
  const ai = plan.data?.reader_status === "used";

  return (
    <>
      <div className="text-[14px] text-faint mb-5"><Crumb to="/p">Courses</Crumb> / {c.code}</div>
      <header className="pb-6">
        <h1 className="font-serif text-[36px] leading-tight">{c.title}</h1>
        <p className="text-muted mt-1 text-[15px]">{c.code} · {c.term} · {c.student_count} students {c.is_synthetic && <SynthTag />}</p>
      </header>

      <Section title="What needs your attention">
        {!main ? <Empty title="Nothing to review yet">Prepare grading evidence for an assignment first.</Empty> : (
          <ul className="divide-y divide-line">
            {waiting.map((iv) => (
              <li key={`w${iv.id}`}><Link to={`/p/interventions/${iv.id}`} className="flex items-center justify-between gap-4 py-4 group">
                <span><span className="block text-ink text-[16px]">Approve or edit: {iv.title}</span><span className="text-[14px] text-muted">A draft for {iv.targets} students is waiting. Nothing has been sent.</span></span>
                <span className="text-accent-ink text-[14px] shrink-0 group-hover:underline underline-offset-4">Review draft →</span></Link></li>
            ))}
            {results.filter((iv) => iv.verified > 0).map((iv) => (
              <li key={`r${iv.id}`}><Link to={`/p/interventions/${iv.id}`} className="flex items-center justify-between gap-4 py-4 group">
                <span><span className="block text-ink text-[16px]">New results: {iv.title}</span><span className="text-[14px] text-muted">{iv.verified} of {iv.delivered} students have completed the new check.</span></span>
                <span className="text-accent-ink text-[14px] shrink-0 group-hover:underline underline-offset-4">See outcomes →</span></Link></li>
            ))}
            {actionable.slice(0, 4).map((g) => {
              const n = g.students.filter((s) => !s.in_intervention).length;
              const fromAI = g.category === "reasoning_gap";
              return (
                <li key={g.category + g.misconception_code}><Link to={`/p/assignments/${main.id}`} className="grid grid-cols-[56px_minmax(0,1fr)_auto] items-center gap-4 py-4 group">
                  <span className="font-serif text-[28px] num leading-none">{n}</span>
                  <span className="min-w-0">
                    <span className="block text-ink text-[16px]">{g.label.split(" · ")[0]}{g.misconception_code ? `: ${misconceptionLabel(g.misconception_code).toLowerCase()}` : ""}</span>
                    <span className="flex flex-wrap items-center gap-2 mt-1"><EvidenceTag kind="test" />{fromAI && <EvidenceTag kind={ai ? "ai" : "rules"} />}<span className="text-[14px] text-faint">{main.title.split("—")[0].trim()}</span></span>
                  </span>
                  <span className="text-accent-ink text-[14px] shrink-0 group-hover:underline underline-offset-4">Review →</span>
                </Link></li>
              );
            })}
            {waiting.length + actionable.length === 0 && <li className="py-4 text-muted">Nothing new. Every group has a plan in progress.</li>}
          </ul>
        )}
      </Section>

      <Section title="Assignments">
        <ul className="divide-y divide-line">
          {c.assignments.filter((a) => !a.targeted).map((a) => (
            <li key={a.id}><Link to={`/p/assignments/${a.id}`} className="flex flex-wrap items-center justify-between gap-3 py-3.5 group">
              <span className="text-ink group-hover:text-accent-ink">{a.title}</span>
              <span className="text-[14px] text-muted num">{a.submitted}/{a.enrolled} submitted · due {fmtDate(a.due_at)}</span>
            </Link></li>
          ))}
        </ul>
        {c.assignments.some((a) => a.targeted) && <p className="text-[14px] text-faint mt-2">Follow-up activities live on each intervention page.</p>}
      </Section>

      <details className="mt-8 border-t border-line pt-5">
        <summary className="cursor-pointer text-[15px] text-muted hover:text-ink">Learning goals and course materials</summary>
        <div className="grid md:grid-cols-[1.6fr_1fr] gap-x-12 mt-4">
          <ol className="space-y-3">
            {c.objectives.map((o) => <li key={o.id}><div className="text-ink" title={o.code}>{o.title}</div>
              {o.misconceptions.length > 0 && <div className="text-[14px] text-faint mt-0.5">Watch for: {o.misconceptions.map((m) => misconceptionLabel(m.code).toLowerCase()).join("; ")}</div>}</li>)}
          </ol>
          <ul className="space-y-2 text-[14px]">{c.materials.map((m) => <li key={m.id} className="text-muted">{m.title}</li>)}</ul>
        </div>
      </details>
    </>
  );
}
