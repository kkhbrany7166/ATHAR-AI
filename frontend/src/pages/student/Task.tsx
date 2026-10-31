import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { StudentTask } from "../../lib/types";
import { Button, CONDITIONS, Crumb, ErrorState, Loading, Tag, cx } from "../../components/ui";

const STEPS = [
  { id: "why", label: "Why this, why now" },
  { id: "think", label: "Think first" },
  { id: "practice", label: "Practise with support" },
  { id: "reflect", label: "Look back" },
  { id: "check", label: "Show what you can do" },
];

export function TaskPage() {
  const { taskId } = useParams();
  const qc = useQueryClient();
  const key = ["task", taskId];
  const q = useQuery({ queryKey: key, queryFn: () => api<StudentTask>(`/api/student/tasks/${taskId}`) });
  const post = (path: string, json?: unknown) => api<StudentTask>(`/api/student/tasks/${taskId}/${path}`, { method: "POST", json: json ?? {} });
  const onOk = (t: StudentTask) => { qc.setQueryData(key, t); qc.invalidateQueries({ queryKey: ["student-home"] }); };

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const t = q.data!;
  const done = {
    why: true, think: !!t.initial_reasoning, practice: t.practice_attempts.some((a) => a.passed === a.total),
    reflect: !!t.revised_reasoning && !!t.reflection, check: t.results.length > 0,
  } as Record<string, boolean>;

  return (
    <>
      <div className="text-[13px] text-faint mb-5"><Crumb to="/s">My learning</Crumb> / {t.course_code}</div>
      <header className="pb-8 max-w-3xl">
        <div className="eyebrow mb-2">From your professor</div>
        <h1 className="font-serif text-[34px] leading-[1.12] tracking-[-0.01em]">{t.title}</h1>
        <p className="text-muted mt-3 text-[16px]">
          A short path in five steps, about twenty minutes. Practice is where help is welcome; the last step is where you show what you can do on your own.
        </p>
      </header>

      <div className="grid lg:grid-cols-[200px_minmax(0,1fr)] gap-x-12">
        <nav className="hidden lg:block">
          <ol className="sticky top-8 space-y-1 text-[14px]">
            {STEPS.map((s, i) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="flex items-center gap-3 py-1.5 text-muted hover:text-ink">
                  <span className={cx("w-6 h-6 rounded-full grid place-items-center text-[12px] num border",
                    done[s.id] ? "bg-accent border-accent text-ink" : "border-line-strong text-faint")}>{done[s.id] ? "✓" : i + 1}</span>
                  {s.label}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0 max-w-[760px] space-y-14">
          <Step id="why" n={1} title="Why this, why now">
            {t.my_earlier_evidence.length > 0 && (
              <p className="text-[16px] text-ink">
                In {t.from_assignment.split("—")[0].trim()}, your code ran into this:{" "}
                {t.my_earlier_evidence.map((e) => <code key={e} className="font-mono text-[13.5px] text-amber bg-amber-wash px-1.5 py-0.5 rounded mr-1">{e}</code>)}
                It's one of the most common places to get stuck with recursion, and a good one to understand properly.
              </p>
            )}
            <div className="mt-6 border-l-2 border-accent-strong pl-5">
              <p className="font-serif text-[17px] leading-[1.75] text-ink whitespace-pre-line">{t.explanation}</p>
            </div>
          </Step>

          <Step id="think" n={2} title="Think first" badge={<Tag>Just your thinking. Not graded</Tag>}>
            <p className="text-muted mb-4">{t.practice?.explanation_prompt} Write what you think now, before any help. You'll look back at it later.</p>
            <Checkpoint value={t.initial_reasoning} placeholder="I think it should return…" onSave={(text) => post("checkpoint", { kind: "initial", text }).then(onOk)} />
          </Step>

          {t.practice && (
            <Step id="practice" n={3} title="Practise with support" badge={<Tag tone="accent">Assisted practice</Tag>}>
              <Practice t={t} post={post} onOk={onOk} />
            </Step>
          )}

          <Step id="reflect" n={4} title="Look back">
            <div className="space-y-6">
              <div>
                <p className="text-muted mb-3">Answer the same question again: {t.practice?.explanation_prompt}</p>
                {t.initial_reasoning && <p className="text-[14px] text-faint mb-3">Earlier you wrote: <span className="italic">“{t.initial_reasoning}”</span></p>}
                <Checkpoint value={t.revised_reasoning} placeholder="Now I think…" onSave={(text) => post("checkpoint", { kind: "revised", text }).then(onOk)} />
              </div>
              <div>
                <p className="text-muted mb-3">What changed in how you think about where recursion stops?</p>
                <Checkpoint value={t.reflection} placeholder="What I understand differently now is…" onSave={(text) => post("checkpoint", { kind: "reflection", text }).then(onOk)} />
              </div>
            </div>
          </Step>

          {t.check && (
            <Step id="check" n={5} title="Show what you can do" badge={<Tag>{CONDITIONS[t.check.conditions]?.label}</Tag>}>
              <FollowUp t={t} post={post} onOk={onOk} />
            </Step>
          )}
        </div>
      </div>
    </>
  );
}

function Step({ id, n, title, badge, children }: { id: string; n: number; title: string; badge?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-8">
      <div className="flex flex-wrap items-center gap-3 border-b border-line pb-3 mb-5">
        <span className="font-serif text-[15px] text-faint num">{n}</span>
        <h2 className="font-serif text-[22px]">{title}</h2>
        {badge && <span className="ml-auto">{badge}</span>}
      </div>
      {children}
    </section>
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
    <textarea value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={onKey} rows={rows} spellCheck={false}
      aria-label="Code editor" className="w-full bg-canvas border border-line-strong rounded-md px-4 py-3 font-mono text-[13.5px] leading-[1.65] text-ink" />
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
  const [code, setCode] = useState(c.starter_code);
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
          <p className="text-muted mt-1">{RESULT_NEXT[last.outcome]}</p>
          <ul className="mt-3 space-y-1 text-[14px] text-muted list-disc ml-4">{last.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          <div className="text-[12.5px] text-faint mt-2 num">{last.tests_passed}/{last.tests_total} tests passed · attempt {t.results.length}</div>
        </div>
      )}
      {!closed && (
        <>
          <CodeEditor value={code} onChange={setCode} rows={8} />
          <div>
            <label className="block text-muted mb-2" htmlFor="fx">{c.explanation_prompt}</label>
            <textarea id="fx" value={explanation} onChange={(e) => setExplanation(e.target.value)} rows={4}
              className="w-full bg-surface border border-line-strong rounded-md px-4 py-3 text-[15px]" />
          </div>
          <div>
            <label className="block text-[13.5px] text-faint mb-1.5" htmlFor="dx">Did you use any outside help or AI tools? (optional, and honest answers are never penalised)</label>
            <input id="dx" value={disclosure} onChange={(e) => setDisclosure(e.target.value)}
              className="w-full h-9 bg-surface border border-line rounded px-3 text-[14px]" />
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-[13px] text-faint">Checked with tests you can't see yet, plus your explanation.</span>
            <Button variant="primary" disabled={submit.isPending || !code.trim()} onClick={() => submit.mutate()}>
              {submit.isPending ? "Checking…" : last ? "Submit another attempt" : "Submit"}
            </Button>
          </div>
          {submit.error && <p className="text-brick text-[13px]">{(submit.error as Error).message}</p>}
        </>
      )}
    </div>
  );
}
