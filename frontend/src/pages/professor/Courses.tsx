import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { CourseDetail, CourseSummary } from "../../lib/types";
import { CONDITIONS, Crumb, Empty, ErrorState, KIND, Loading, PageHeader, Section, SynthTag, Tag, fmtDate } from "../../components/ui";
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
                <div className="text-[12.5px] text-muted mt-0.5 num">{c.term} · {c.student_count} students · {c.assignment_count} {c.assignment_count === 1 ? "assignment" : "assignments"}</div>
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
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const c = q.data!;
  const attention = c.assignments.flatMap((a) => a.insights.map((i) => ({ ...i, assignment: a })));

  return (
    <>
      <div className="text-[12px] text-faint mb-5"><Crumb to="/p">Courses</Crumb> / {c.code}</div>
      <PageHeader
        eyebrow={<span className="flex items-center gap-2">{c.code} · {c.term} {c.is_synthetic && <SynthTag />}</span>}
        title={c.title}
      >
        {c.description} <span className="num">{c.student_count} students enrolled.</span>
      </PageHeader>

      <Section title="What needs your attention" aside="From the latest prepared grading evidence">
        {attention.length === 0 ? (
          <Empty title="No insights yet">
            Prepare grading evidence for an assignment and ATHAR will connect the results to your learning objectives.
          </Empty>
        ) : (
          <ul className="divide-y divide-line">
            {attention.map((i) => (
              <li key={i.id}>
                <Link to={`/p/insights/${i.id}`} className="grid grid-cols-[64px_1fr_auto] items-center gap-4 py-3.5 group">
                  <span className="font-serif text-[26px] text-ink num leading-none">{i.student_count}</span>
                  <span className="min-w-0">
                    <span className="block text-ink">{i.title}</span>
                    <span className="block text-[12.5px] text-muted truncate">
                      {i.kind === "misconception" ? "Possible misconception" : "Support"} · {i.assignment.title}
                    </span>
                  </span>
                  <span className="text-[13px] text-faint group-hover:text-accent-ink">Review evidence →</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Assignments">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-faint text-2xs uppercase tracking-[0.1em]">
              <th className="font-medium pb-2">Title</th><th className="font-medium pb-2">Type</th>
              <th className="font-medium pb-2">Due</th><th className="font-medium pb-2 text-right">Submitted</th>
              <th className="font-medium pb-2 text-right">Evidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line border-t border-line">
            {c.assignments.map((a) => (
              <tr key={a.id}>
                <td className="py-3 pr-4"><Link to={`/p/assignments/${a.id}`} className="link">{a.title}</Link></td>
                <td className="py-3 pr-4 text-muted">{KIND[a.kind] ?? a.kind} · {CONDITIONS[a.conditions]?.label ?? a.conditions}</td>
                <td className="py-3 pr-4 text-muted">{fmtDate(a.due_at)}</td>
                <td className="py-3 text-right num">{a.submitted} / {a.enrolled}</td>
                <td className="py-3 text-right">
                  {!a.latest_run ? <Tag>Not prepared</Tag>
                    : a.latest_run.status === "done" ? <Tag tone="accent">Prepared</Tag>
                    : a.latest_run.status === "failed" ? <Tag tone="brick">Failed</Tag>
                    : <Tag tone="amber">Running</Tag>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <div className="grid md:grid-cols-[1.6fr_1fr] gap-x-12">
        <Section title="Learning objectives" aside="Authored with the rubric">
          <ol className="space-y-4">
            {c.objectives.map((o) => (
              <li key={o.id} className="grid grid-cols-[52px_1fr] gap-3">
                <span className="font-mono text-[12px] text-accent-ink pt-0.5">{o.code}</span>
                <div>
                  <div className="text-ink">{o.title}</div>
                  {o.misconceptions.length > 0 && (
                    <div className="text-[12.5px] text-faint mt-1">
                      Misconceptions to watch for: {o.misconceptions.map((m) => m.title.toLowerCase()).join("; ")}.
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Section>
        <Section title="Course materials">
          <ul className="space-y-2 text-[13px]">
            {c.materials.map((m) => (
              <li key={m.id} className="flex justify-between gap-3">
                <span>{m.title}</span><span className="text-faint">{m.kind.replace("_", " ")}</span>
              </li>
            ))}
          </ul>
          <p className="text-2xs text-faint mt-4">Uploading PDFs and notes arrives in milestone 3.</p>
        </Section>
      </div>
    </>
  );
}
