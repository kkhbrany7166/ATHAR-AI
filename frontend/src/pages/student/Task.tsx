import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { StudentTask } from "../../lib/types";
import { Button, CONDITIONS, Crumb, ErrorState, Loading, Tag, cx } from "../../components/ui";

const STEPS_BY_KIND: Record<string, { id: string; label: string }[]> = {
  concept_practice: [
    { id: "why", label: "Why this" }, { id: "think", label: "Think first" }, { id: "practice", label: "Practise with help" },
    { id: "reflect", label: "Look back" }, { id: "check", label: "Show it" },
  ],
  debugging: [{ id: "why", label: "Why this" }, { id: "check", label: "Fix the program" }],
  explain_reasoning: [{ id: "why", label: "Why this" }, { id: "check", label: "Explain your own code" }],
};
const INTRO: Record<string, string> = {
  concept_practice: "A short path in five steps, about twenty minutes. Practice is where help is welcome; the last step is where you show what you can do on your own.",
  debugging: "A short exercise, about ten minutes. Your code didn't run last time, so the tests never got to show what you understand. Let's fix that first.",
  explain_reasoning: "One short written task, about ten minutes. Your code already works. This is about putting into words why it stops.",
};

export function TaskPage() {
  const { taskId } = useParams();
  const qc = useQueryClient();
  const key = ["task", taskId];
  const [active, setActive] = useState<string | null>(null);
  const q = useQuery({ queryKey: key, queryFn: () => api<StudentTask>(`/api/student/tasks/${taskId}`) });
  useEffect(() => {  // keep the current step visible in the step bar on narrow screens
    document.querySelector('[aria-current="step"]')?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [active, q.data]);
  const post = (path: string, json?: unknown) => api<StudentTask>(`/api/student/tasks/${taskId}/${path}`, { method: "POST", json: json ?? {} });
  const onOk = (t: StudentTask) => { qc.setQueryData(key, t); qc.invalidateQueries({ queryKey: ["student-home"] }); };

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const t = q.data!;
  const STEPS = STEPS_BY_KIND[t.kind] ?? STEPS_BY_KIND.concept_practice;
  const done = {
    why: true, think: !!t.initial_reasoning, practice: t.practice_attempts.some((a) => a.passed === a.total),
    reflect: !!t.revised_reasoning, check: t.results.length > 0,
  } as Record<string, boolean>;
  const current = active ?? (STEPS.find((s) => s.id !== "why" && !done[s.id])?.id ?? STEPS[STEPS.length - 1].id);
  const idx = STEPS.findIndex((s) => s.id === current);
  const go = (id: string) => { setActive(id); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const step = STEPS[idx];

  return (
    <>
      <div className="text-[13px] text-faint mb-5"><Crumb to="/s">My learning</Crumb> / {t.course_code}</div>
      <header className="pb-6 max-w-3xl">
        <div className="eyebrow mb-2">From your professor</div>
        <h1 className="font-serif text-[32px] sm:text-[36px] leading-[1.12] tracking-[-0.01em]">{t.title}</h1>
        <p className="text-muted mt-3 text-[16px]">{INTRO[t.kind] ?? INTRO.concept_practice}</p>
      </header>

      {/* Step bar: visible on every screen size; any step can be revisited */}
      <nav aria-label="Activity steps" className="border-y border-line -mx-4 px-4 sm:mx-0 sm:px-0 overflow-x-auto">
        <ol className="flex min-w-max">
          {STEPS.map((s, i) => {
            const isCurrent = s.id === current;
            const independent = s.id === "check";
            return (
              <li key={s.id} className="flex items-center">
                <button onClick={() => go(s.id)} aria-current={isCurrent ? "step" : undefined}
                  className={cx("flex items-center gap-2.5 h-14 pr-5 text-[14.5px] border-b-2 -mb-px transition-colors",
                    isCurrent ? "border-accent-strong text-ink" : "border-transparent text-muted hover:text-ink")}>
                  <span className={cx("w-7 h-7 rounded-full grid place-items-center text-[13px] num border shrink-0",
                    done[s.id] && s.id !== "why" ? "bg-accent border-accent text-ink" : isCurrent ? "border-accent-strong text-ink" : "border-line-strong text-faint")}>
                    {done[s.id] && s.id !== "why" ? "✓" : i + 1}
                  </span>
                  <span className="whitespace-nowrap">{s.label}</span>
                  {independent && <span className="text-[12px] text-faint whitespace-nowrap">on your own</span>}
                </button>
                {i < STEPS.length - 1 && <span aria-hidden className="text-line-strong pr-5">—</span>}
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="max-w-[820px] pt-8 min-h-[50vh]">
        <h2 className="font-serif text-[26px] mb-1">{step.label}</h2>
        <p className="text-[14px] text-faint mb-6">Step {idx + 1} of {STEPS.length}{step.id === "practice" ? " · help is welcome here" : step.id === "check" ? " · this part is on your own" : ""}</p>

        {step.id === "why" && (
          <div>
            {t.my_earlier_evidence.length > 0 && (
              <div className="mb-6">
                <div className="text-[14px] text-faint mb-2">In {t.from_assignment.split("—")[0].trim()}, {t.kind === "explain_reasoning" ? "your code worked, and you wrote:" : "your code ran into this:"}</div>
                <div className="flex flex-wrap gap-2">{t.my_earlier_evidence.map((e) => <code key={e} className="font-mono text-[14px] text-amber bg-amber-wash px-2 py-1 rounded">{e}</code>)}</div>
                <p className="text-muted mt-3 text-[15px]">It's one of the most common places to get stuck with recursion, and a good one to understand properly. Nothing here is graded until the last step.</p>
              </div>
            )}
            <div className="border-l-2 border-accent-strong pl-5">
              <p className="font-serif text-[17.5px] leading-[1.8] text-ink whitespace-pre-line">{t.explanation}</p>
            </div>
          </div>
        )}

        {step.id === "think" && (
          <div>
            <p className="text-ink text-[16px] mb-1">{t.practice?.explanation_prompt}</p>
            <p className="text-muted mb-4 text-[15px]">Write what you think now, before any help. It isn't graded, and you'll compare it with your answer later.</p>
            <Checkpoint value={t.initial_reasoning} placeholder="I think it should return…" onSave={(text) => post("checkpoint", { kind: "initial", text }).then(onOk)} />
          </div>
        )}

        {step.id === "practice" && t.practice && (
          <div className="border-l-2 border-accent/70 pl-5">
            <Practice t={t} post={post} onOk={onOk} />
          </div>
        )}

        {step.id === "reflect" && (
          <div className="space-y-6">
            <p className="text-ink text-[16px]">Answer the same question again: {t.practice?.explanation_prompt}</p>
            <div className="grid md:grid-cols-2 gap-5">
              <div>
                <div className="eyebrow mb-2">Before practice</div>
                <p className="text-muted italic bg-surface border border-line rounded-md px-4 py-3 min-h-[72px]">{t.initial_reasoning ? `“${t.initial_reasoning}”` : "You skipped this. That's fine."}</p>
              </div>
              <div>
                <div className="eyebrow mb-2">Now</div>
                <Checkpoint value={t.revised_reasoning} placeholder="Now I think…" onSave={(text) => post("checkpoint", { kind: "revised", text }).then(onOk)} />
              </div>
            </div>
            <details className="text-[15px]">
              <summary className="cursor-pointer text-muted hover:text-ink">Optional: note what changed in your thinking</summary>
              <div className="mt-3"><Checkpoint value={t.reflection} placeholder="What I understand differently now is…" onSave={(text) => post("checkpoint", { kind: "reflection", text }).then(onOk)} /></div>
            </details>
          </div>
        )}

        {step.id === "check" && t.check && (
          <div className="border border-line-strong rounded-lg p-5 sm:p-6">
            <div className="flex flex-wrap items-center gap-2 mb-4"><Tag>{CONDITIONS[t.check.conditions]?.label}</Tag><span className="text-[13.5px] text-faint">No hints or assistant here. That's what makes it your own evidence.</span></div>
            <FollowUp t={t} post={post} onOk={onOk} />
          </div>
        )}

        <div className="flex items-center justify-between gap-3 mt-10 pt-5 border-t border-line">
          {idx > 0 ? <Button variant="ghost" onClick={() => go(STEPS[idx - 1].id)}>← {STEPS[idx - 1].label}</Button> : <span />}
          {idx < STEPS.length - 1 && <Button variant="primary" onClick={() => go(STEPS[idx + 1].id)}>{STEPS[idx + 1].label} →</Button>}
        </div>
      </div>
    </>
  );
}

function Checkpoint({ value, placeholder, onSave }: { value: string; placeholder: string; onSave: (t: string) => Promise<unknown> }) {
  const [text, setText] = useState(value);
  const [editing, setEditing] = useState(!value);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setText(value); setEditing(!value); }, [value]);
  if (!editing) {
    return (
      <div className="flex items-start justify-between gap-4 bg-surface border border-line rounded-md px-4 py-3">
        <p className="text-ink whitespace-pre-line">{value}</p>
        <button className="link text-[13px] shrink-0" onClick={() => setEditing(true)}>Edit</button>
      </div>
    );
  }
  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder={placeholder}
        className="w-full bg-surface border border-line-strong rounded-md px-4 py-3 text-[15px] placeholder:text-faint" />
      <div className="flex justify-end mt-2">
        <Button disabled={!text.trim() || busy} onClick={async () => { setBusy(true); try { await onSave(text); } finally { setBusy(false); } }}>
          {busy ? "Saving…" : "Save checkpoint"}
        </Button>
      </div>
    </div>
  );
}

function CodeEditor({ value, onChange, rows = 10 }: { value: string; onChange: (v: string) => void; rows?: number }) {
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const el = e.currentTarget;
    const { selectionStart: s, selectionEnd: end } = el;
    const next = value.slice(0, s) + "    " + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = s + 4; });
  };
  return (
    <textarea value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={onKey} rows={rows} spellCheck={false} wrap="off"
      aria-label="Code editor" className="w-full whitespace-pre overflow-x-auto bg-canvas border border-line-strong rounded-md px-4 py-3 font-mono text-[13.5px] leading-[1.65] text-ink" />
  );
}

type Post = (path: string, json?: unknown) => Promise<StudentTask>;

function Practice({ t, post, onOk }: { t: StudentTask; post: Post; onOk: (t: StudentTask) => void }) {
  const p = t.practice!;
  const last = t.practice_attempts[t.practice_attempts.length - 1];
  const [code, setCode] = useState(last?.code ?? p.starter_code);
  const run = useMutation({ mutationFn: () => post("practice", { code }), onSuccess: onOk });
  const hint = useMutation({ mutationFn: () => post("hint"), onSuccess: onOk });
  return (
    <div className="space-y-6">
      <p className="text-ink text-[16px]">{p.prompt}</p>
      <div>
        <CodeEditor value={code} onChange={setCode} />
        <div className="flex flex-wrap items-center justify-between gap-3 mt-2">
          <span className="text-[13px] text-faint">Runs your code against {p.tests.length} tests in a safe sandbox.</span>
          <Button variant="primary" onClick={() => run.mutate()} disabled={run.isPending}>{run.isPending ? "Running…" : "Run tests"}</Button>
        </div>
        {run.error && <p className="text-brick text-[13px] mt-2">{(run.error as Error).message}</p>}
      </div>
      {last && (
        <div className={cx("rounded-md border px-4 py-3", last.passed === last.total ? "border-accent/60 bg-accent-wash/50" : "border-line-strong bg-surface")}>
          <div className="text-[14px] text-ink mb-2">
            {last.passed === last.total ? "All tests pass. Nice work. Notice which case needed the most thought." : `${last.passed} of ${last.total} tests pass. Look at the one that doesn't: what input is it?`}
          </div>
          <ul className="space-y-1 font-mono text-[12.5px]">
            {last.results.map((r) => (
              <li key={r.name} className={r.status === "pass" ? "text-accent-ink" : "text-amber"}>
                {r.status === "pass" ? "✓" : "✗"} {r.name}{r.status !== "pass" && <span className="text-faint"> · {r.error_type || `got ${r.actual}`}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <div className="eyebrow mb-2">Hints ({t.hints.length} of {p.hint_count})</div>
          <ol className="space-y-2 text-[14.5px]">
            {t.hints.map((h, i) => <li key={i} className="border-l-2 border-line-strong pl-3 text-muted"><span className="text-faint mr-1.5">{i + 1}.</span>{h}</li>)}
          </ol>
          {t.hints.length < p.hint_count && (
            <button className="link text-[14px] mt-3" onClick={() => hint.mutate()} disabled={hint.isPending}>
              {t.hints.length === 0 ? "Show a first nudge" : "Show the next hint"}
            </button>
          )}
          <p className="text-[12.5px] text-faint mt-3">Using hints is part of practising. It never counts against you.</p>
        </div>
        <Assistant t={t} post={post} onOk={onOk} />
      </div>
    </div>
  );
}

function Assistant({ t, post, onOk }: { t: StudentTask; post: Post; onOk: (t: StudentTask) => void }) {
  const [msg, setMsg] = useState("");
  const ask = useMutation({ mutationFn: () => post("assistant", { message: msg }), onSuccess: (r) => { setMsg(""); onOk(r); } });
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [t.messages.length]);
  return (
    <div className="flex flex-col">
      <div className="eyebrow mb-2">Ask the course assistant</div>
      <div className="flex-1 max-h-64 overflow-y-auto space-y-2.5 text-[14px] mb-2">
        {t.messages.length === 0 && <p className="text-faint">Ask about the idea, not for the answer. For example: “why does the empty list break my function?”</p>}
        {t.messages.map((m) => (
          <div key={m.id} className={cx(m.role === "student" ? "text-ink" : m.role === "system" ? "text-faint italic" : "text-muted border-l-2 border-accent-strong pl-3")}>
            {m.role === "student" && <span className="text-faint mr-1">You:</span>}{m.content}
            {m.source.startsWith("ai:") && <span className="block text-2xs text-faint mt-0.5">AI · {m.source.slice(3)}</span>}
          </div>
        ))}
        <div ref={end} />
      </div>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (msg.trim()) ask.mutate(); }}>
        <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Your question"
          className="flex-1 min-w-0 h-9 bg-surface border border-line-strong rounded px-3 text-[14px] placeholder:text-faint" />
        <Button type="submit" disabled={!msg.trim() || ask.isPending}>Ask</Button>
      </form>
    </div>
  );
}

const RESULT_TONE: Record<string, string> = {
  demonstrated: "border-accent/60 bg-accent-wash/50", still_developing: "border-amber/40 bg-amber-wash/60", insufficient_evidence: "border-line-strong bg-surface",
};
const RESULT_NEXT: Record<string, string> = {
  demonstrated: "This task shows you can find the smallest input and stop there. Your professor can see this too.",
  still_developing: "That's useful to know, not a verdict. Look at the reason below, revisit the practice, and try again whenever you're ready.",
  insufficient_evidence: "Your professor will take a look. Adding a clear explanation of where and why it stops usually settles it.",
};

function FollowUp({ t, post, onOk }: { t: StudentTask; post: Post; onOk: (t: StudentTask) => void }) {
  const c = t.check!;
  const [code, setCode] = useState(t.kind === "explain_reasoning" ? t.my_original_code : c.starter_code);
  const explainOnly = t.kind === "explain_reasoning";
  const [explanation, setExplanation] = useState("");
  const [disclosure, setDisclosure] = useState("");
  const submit = useMutation({ mutationFn: () => post("followup", { code, explanation, ai_use_disclosure: disclosure }), onSuccess: onOk });
  const last = t.results[t.results.length - 1];
  const closed = t.intervention_status !== "active";
  return (
    <div className="space-y-5">
      <p className="text-muted text-[14.5px]">{c.ai_policy}</p>
      <p className="text-ink text-[16px]">{c.prompt}</p>
      {last && (
        <div className={cx("rounded-md border px-5 py-4", RESULT_TONE[last.outcome])}>
          <div className="font-serif text-[20px] text-ink">{last.label}</div>
          <p className="text-muted mt-1">{last.outcome === "demonstrated" && t.kind !== "concept_practice"
            ? (t.kind === "debugging" ? "Your program runs and passes every test, so your recursion can now be checked properly. Your professor can see this."
               : "Your explanation names where and why the recursion stops. Your professor can see this.")
            : RESULT_NEXT[last.outcome]}</p>
          <ul className="mt-3 space-y-1 text-[14px] text-muted list-disc ml-4">{last.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          <div className="text-[12.5px] text-faint mt-2 num">{last.tests_passed}/{last.tests_total} tests passed · attempt {t.results.length}</div>
        </div>
      )}
      {!closed && (
        <>
          {explainOnly ? (
            <div><div className="eyebrow mb-2">Your Assignment 3 code</div><pre className="font-mono text-[13px] bg-canvas border border-line rounded-md p-4 overflow-x-auto">{t.my_original_code}</pre></div>
          ) : <CodeEditor value={code} onChange={setCode} rows={8} />}
          <div>
            <label className="block text-muted mb-2" htmlFor="fx">{explainOnly ? "Your explanation" : t.kind === "debugging" ? `${c.explanation_prompt} (optional)` : c.explanation_prompt}</label>
            <textarea id="fx" value={explanation} onChange={(e) => setExplanation(e.target.value)} rows={4}
              className="w-full bg-surface border border-line-strong rounded-md px-4 py-3 text-[15px]" />
          </div>
          <div>
            <label className="block text-[13.5px] text-faint mb-1.5" htmlFor="dx">Did you use any outside help or AI tools? (optional, and honest answers are never penalised)</label>
            <input id="dx" value={disclosure} onChange={(e) => setDisclosure(e.target.value)}
              className="w-full h-9 bg-surface border border-line rounded px-3 text-[14px]" />
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[13px] text-faint">{explainOnly ? "Your explanation is read and checked against the stopping condition. Your code is not re-graded." :
              t.kind === "debugging" ? "Runs your fixed program against the tests." : "Checked with tests you can't see yet, plus your explanation."}</span>
            <Button variant="primary" disabled={submit.isPending || (explainOnly ? !explanation.trim() : !code.trim())} onClick={() => submit.mutate()}>
              {submit.isPending ? "Checking…" : last ? "Submit another attempt" : "Submit"}
            </Button>
          </div>
          {submit.error && <p className="text-brick text-[13px]">{(submit.error as Error).message}</p>}
        </>
      )}
    </div>
  );
}
