import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { objectiveLabel } from "../../lib/labels";
import { EvidenceTag, sourceKind } from "../../components/Evidence";
import type { InsightDetail, InsightEvidence } from "../../lib/types";
import { Button, CONDITIONS, Callout, Crumb, ErrorState, KIND, Loading, Meter, Section, SynthTag } from "../../components/ui";

function pct(n: number, d: number) {
  return d ? `${Math.round((100 * n) / d)}%` : "—";
}

export function InsightPage() {
  const { insightId } = useParams();
  const q = useQuery({ queryKey: ["insight", insightId], queryFn: () => api<InsightDetail>(`/api/professor/insights/${insightId}`) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const i = q.data!;
  if (i.kind !== "misconception") {
    return <Callout title={i.title}>{i.summary} <Link className="link" to={`/p/assignments/${i.assignment.id}`}>Back to the assignment</Link></Callout>;
  }
  const e = i.evidence as InsightEvidence;
  const c = e.counts;
  const others = c.submitted - c.students;
  const linked = e.criteria.filter((x) => x.linked);
  const unlinked = e.criteria.filter((x) => !x.linked);

  return (
    <>
      <div className="text-[13px] text-faint mb-5">
        <Crumb to="/p">Courses</Crumb> / <Crumb to={`/p/courses/${i.assignment.course_id}`}>{i.assignment.course_code}</Crumb> /{" "}
        <Crumb to={`/p/assignments/${i.assignment.id}`}>{i.assignment.title.split("—")[0].trim()}</Crumb> / Insight
      </div>

      <header className="pb-6">
        <div className="eyebrow mb-2 flex items-center gap-2">
          Possible misconception{i.objective && <span title={i.objective.code}> · {objectiveLabel(i.objective.code)}</span>}
        </div>
        <h1 className="font-serif text-[32px] leading-[1.15] tracking-[-0.01em] max-w-3xl">{i.title}</h1>
        <p className="text-muted mt-3 max-w-prose">{e.misconception.description}</p>
      </header>

      {/* The numbers, all derived from stored evidence */}
      <div className="grid grid-cols-2 md:grid-cols-4 border-y border-line divide-x divide-line">
        <Figure value={c.students} label={`submissions flagged, of ${c.submitted}`} />
        <Figure value={c.tests_only + c.both} label="flagged by a failing test" kind="test" />
        <Figure value={c.explanation_only + c.both} label="flagged by the AI reading of the explanation" kind="ai" />
        <Figure value={c.working_code_confused_reasoning} label="pass every test, flagged only by the AI reading" tone={c.working_code_confused_reasoning ? "amber" : undefined} />
      </div>
      <p className="text-[14px] text-muted mt-3 max-w-prose">
        {c.tests_only + c.both > 0 && <>Test flags are deterministic: the code failed in the way this misconception predicts. </>}
        {c.explanation_only + c.both > 0 && <>Explanation flags are AI suggestions, quoted word for word below. They are not diagnoses until you review them, and on
          this synthetic class the AI reader over-flags (see Evaluation).</>}
      </p>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_300px] gap-x-12">
        <div>
          {e.examples.length > 0 && (
            <Section title="From student work" aside={`${e.examples.length} of ${c.students} shown`}>
              <ul className="space-y-6">
                {e.examples.map((x) => (
                  <li key={x.submission_id} className="grid grid-cols-[3px_1fr] gap-4">
                    <span className="bg-line-strong rounded-full" />
                    <div>
                      {x.quote ? (
                        <blockquote className="font-serif text-[17px] leading-[1.55] text-ink">“{x.quote}”</blockquote>
                      ) : (
                        <div className="text-muted text-[14px] italic">No explanation quote. Evidence comes from tests.</div>
                      )}
                      {x.test_evidence && <div className="font-mono text-[13px] text-brick mt-2">{x.test_evidence}</div>}
                      <div className="flex flex-wrap items-center gap-2 mt-2 text-[13.5px] text-muted">
                        <span>{x.student_name}</span>
                        {x.is_synthetic && <SynthTag />}
                        {x.sources.map((s) => <EvidenceTag key={s} kind={sourceKind(s)} />)}
                        <Link to={`/p/submissions/${x.submission_id}`} className="link ml-auto">Open submission</Link>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {e.tests.length > 0 && (
            <Section title="Test outcomes" aside="This group compared with the rest of the class">
              <table className="w-full text-[14px]">
                <thead>
                  <tr className="text-left text-faint text-2xs uppercase tracking-[0.1em]">
                    <th className="font-medium pb-2">Probe test</th>
                    <th className="font-medium pb-2 w-[150px]">This group passed</th>
                    <th className="font-medium pb-2 w-[150px]">Others passed</th>
                    <th className="font-medium pb-2">Most common failure here</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line border-t border-line">
                  {e.tests.map((t) => (
                    <tr key={t.test_case_id}>
                      <td className="py-3 pr-4 font-mono text-[13px]">{t.name} {t.hidden && <span className="text-faint font-sans">(hidden)</span>}</td>
                      <td className="py-3 pr-4">
                        <div className="num text-[13.5px] mb-1">{t.group_passed}/{t.group_total}</div>
                        <Meter value={t.group_passed} total={t.group_total} tone="brick" />
                      </td>
                      <td className="py-3 pr-4">
                        <div className="num text-[13.5px] mb-1">{t.others_passed}/{t.others_total}</div>
                        <Meter value={t.others_passed} total={t.others_total} />
                      </td>
                      <td className="py-3 text-muted text-[13.5px]">
                        {t.common_failures.map((f) => `${f.kind} (${f.count})`).join(", ") || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          <Section title="Rubric criteria" aside="Share judged “met”: this group / everyone else">
            <table className="w-full text-[14px]">
              <tbody className="divide-y divide-line">
                {[...linked, ...unlinked].map((x) => (
                  <tr key={x.criterion_id} className={x.linked ? "" : "text-faint"}>
                    <td className="py-2.5 pr-4">{x.title}{x.linked && <span className="text-2xs text-accent-ink ml-2">same objective</span>}</td>
                    <td className="py-2.5 pr-4 num text-right whitespace-nowrap">
                      {x.group_judged ? `${pct(x.group_met, x.group_judged)}` : <span className="text-faint" title="No usable judgments">no evidence</span>}
                    </td>
                    <td className="py-2.5 num text-right whitespace-nowrap text-muted">
                      {x.others_judged ? pct(x.others_met, x.others_judged) : "no evidence"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Why it matters">
            <p className="max-w-prose text-muted">{e.why_it_matters}</p>
          </Section>

          <Section title="Next step">
            <NextStep insightId={i.id} count={c.students} drafted={i.status === "intervention_drafted"} />
          </Section>
        </div>

        <aside className="lg:pt-6 space-y-8 text-[14px]">
          <div>
            <div className="eyebrow mb-2">Assessment conditions</div>
            <div className="text-ink">{KIND[e.conditions.kind] ?? e.conditions.kind} · {CONDITIONS[e.conditions.conditions]?.label}</div>
            <p className="text-muted mt-1">{CONDITIONS[e.conditions.conditions]?.help}</p>
            <p className="text-faint mt-2 text-[13.5px]">{e.conditions.ai_policy}</p>
          </div>

          {e.contradictions.length > 0 && (
            <div>
              <div className="eyebrow mb-2">Evidence that disagrees</div>
              <ul className="space-y-2">
                {e.contradictions.map((x) => <li key={x.kind} className="text-muted">{x.text}</li>)}
              </ul>
            </div>
          )}

          <div>
            <div className="eyebrow mb-2">Missing or weak evidence</div>
            {e.missing.length === 0 ? <p className="text-faint">None recorded.</p> : (
              <ul className="space-y-2">{e.missing.map((x) => <li key={x.kind} className="text-muted">{x.text}</li>)}</ul>
            )}
          </div>

          <div>
            <div className="eyebrow mb-2">How this was found</div>
            <p className="text-faint leading-5">
              Probe tests are run in a sandbox. A failure counts as evidence only when it fails the way the rubric describes.
              Explanation evidence counts only when an AI-quoted span appears word for word in the student's text.
              Patterns are reported once at least {e.threshold} students show them. This is a lead for your judgment, not a diagnosis.
            </p>
          </div>

          <div>
            <div className="eyebrow mb-2">Students in this group ({c.students})</div>
            <StudentList ids={e.submission_ids} examples={e.examples} assignmentId={i.assignment.id} />
          </div>
        </aside>
      </div>
      <p className="text-2xs text-faint mt-10">Students who didn't submit: {c.enrolled - c.submitted}. Everyone else who submitted: {others}.</p>
    </>
  );
}

function Figure({ value, label, tone, kind }: { value: number; label: string; tone?: "amber"; kind?: "test" | "ai" }) {
  return (
    <div className="py-4 px-4 first:pl-0">
      <div className={`font-serif text-[30px] leading-none num ${tone === "amber" ? "text-amber" : ""}`}>{value}</div>
      <div className="text-[13.5px] text-muted mt-1.5 leading-5">{label}</div>
      {kind && <div className="mt-2"><EvidenceTag kind={kind} /></div>}
    </div>
  );
}

function StudentList({ ids, assignmentId }: { ids: number[]; examples: InsightEvidence["examples"]; assignmentId: number }) {
  const q = useQuery({
    queryKey: ["submissions", String(assignmentId)],
    queryFn: () => api<{ id: number; student: { name: string } }[]>(`/api/professor/assignments/${assignmentId}/submissions`),
  });
  if (!q.data) return <div className="text-faint">…</div>;
  const set = new Set(ids);
  return (
    <ul className="space-y-1 max-h-72 overflow-y-auto pr-2">
      {q.data.filter((s) => set.has(s.id)).map((s) => (
        <li key={s.id}><Link to={`/p/submissions/${s.id}`} className="text-muted hover:text-accent-ink">{s.student.name}</Link></li>
      ))}
    </ul>
  );
}

function NextStep({ insightId, count, drafted }: { insightId: number; count: number; drafted: boolean }) {
  const navigate = useNavigate();
  const draft = useMutation({
    mutationFn: () => api<{ id: number }>(`/api/professor/insights/${insightId}/intervention`, { method: "POST" }),
    onSuccess: (iv) => navigate(`/p/interventions/${iv.id}`),
  });
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <p className="text-muted text-[14px] max-w-prose">
        {drafted
          ? "An intervention for this group already exists. Open it to review or follow progress."
          : `ATHAR will draft a targeted intervention for these ${count} students: a short explanation, practice with progressive hints, and a follow-up check on a new problem. You edit and approve it. Nothing reaches students before you do.`}
      </p>
      <div className="text-right">
        <Button variant="primary" disabled={draft.isPending} onClick={() => draft.mutate()}>
          {draft.isPending ? "Drafting…" : drafted ? "Open intervention" : "Draft an intervention"}
        </Button>
        {draft.error && <p className="text-brick text-[13px] mt-2">{(draft.error as Error).message}</p>}
      </div>
    </div>
  );
}
