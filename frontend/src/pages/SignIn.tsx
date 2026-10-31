import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { UserBrief } from "../lib/types";
import { LogoMark } from "../components/Logo";
import { cx } from "../components/ui";

interface Highlight {
  available: boolean; course_code?: string; students?: number; submitted?: number;
  headline?: string; detail?: string; source?: string;
}

const LOOP = [
  ["Assess", "Tests and rubric evidence for every submission"],
  ["Understand", "Patterns traced back to real student work"],
  ["Intervene", "Targeted help you review and approve"],
  ["Verify", "A new task shows what has changed"],
];

export function SignIn() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<number | null>(null);
  const [other, setOther] = useState("");
  const people = useQuery({
    queryKey: ["personas"],
    queryFn: () => api<{ personas: UserBrief[]; other_students: UserBrief[] }>("/api/auth/personas"),
  });
  const moment = useQuery({ queryKey: ["highlight"], queryFn: () => api<Highlight>("/api/public/highlight") });
  const prof = people.data?.personas.find((p) => p.role === "professor");
  const sara = people.data?.personas.find((p) => p.role === "student");

  const enter = async (id: number) => {
    setBusy(id);
    try {
      const u = await signIn(id);
      navigate(u.role === "professor" ? "/p" : "/s");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full max-w-[1200px] mx-auto px-5 sm:px-10 pt-7 pb-5 flex items-center justify-between border-b border-line">
        <span className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-md bg-accent/90 grid place-items-center"><LogoMark size={24} light /></span>
          <span className="flex items-baseline gap-2">
            <span className="text-[19px] font-semibold tracking-[0.04em]">ATHAR</span>
            <span className="font-arabic text-[19px] text-accent-ink">أثر</span>
          </span>
        </span>
        <span className="hidden sm:block text-[14px] text-muted">More time to teach. More room to learn.</span>
      </header>

      <main className="flex-1 w-full max-w-[1200px] mx-auto px-5 sm:px-10">
        <section className="grid lg:grid-cols-[1.15fr_1fr] gap-x-16 gap-y-10 pt-14 lg:pt-20 pb-14">
          <div>
            <div className="eyebrow text-accent-ink/90">For the people behind the classroom</div>
            <h1 className="font-serif text-[40px] sm:text-[54px] leading-[1.06] tracking-[-0.015em] mt-5">
              Behind every answer<br className="hidden sm:block" /> is a student.
            </h1>
            <p className="text-[18px] leading-[1.6] text-muted mt-6 max-w-[34em]">
              See where students need help, and reach them before they fall behind. ATHAR reads the evidence in their work,
              so the time you spend goes to teaching, and the help students get leaves them room to think.
            </p>
          </div>

          <figure className="self-end border border-line-strong rounded-lg bg-surface">
            <figcaption className="flex items-center justify-between px-6 pt-5 text-[13px] text-faint">
              <span className="eyebrow">A moment in the classroom</span>
              <span>{moment.data?.course_code ?? "CS201"}</span>
            </figcaption>
            <div className="px-6 pt-4 pb-6">
              {moment.data?.available ? (
                <>
                  <p className="font-serif text-[24px] leading-[1.35] text-ink">{moment.data.headline}</p>
                  <p className="text-[14px] text-muted mt-3">{moment.data.detail}</p>
                </>
              ) : (
                <p className="text-muted text-[15px]">
                  {moment.isLoading ? "Reading the class…" : "No grading evidence yet. Sign in as the professor and prepare it."}
                </p>
              )}
            </div>
            {moment.data?.available && prof && (
              <button onClick={() => enter(prof.id)} disabled={busy !== null}
                className="w-full flex items-center justify-between px-6 py-4 border-t border-line text-[14.5px] text-accent-ink hover:bg-raised/60 transition-colors rounded-b-lg">
                <span>{busy === prof.id ? "Opening…" : "Explore the evidence"}</span><span aria-hidden>↗</span>
              </button>
            )}
          </figure>
        </section>

        <section className="border-t border-line grid sm:grid-cols-2 lg:grid-cols-4">
          {LOOP.map(([step, text], i) => (
            <div key={step} className={cx("py-6 pr-6", i > 0 && "lg:pl-6 lg:border-l border-line", i % 2 === 1 && "sm:pl-6 sm:border-l lg:border-l")}>
              <div className="text-[13px] text-faint num">0{i + 1}</div>
              <div className="text-ink mt-1">{step}</div>
              <div className="text-[14px] text-muted mt-1">{text}</div>
            </div>
          ))}
        </section>

        <section className="border-t border-line pt-10 pb-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3 mb-5">
            <h2 className="font-serif text-[24px]">Explore the demo</h2>
            <p className="text-[13.5px] text-faint">A fictional course with fictional people. No sign-up, no passwords.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              { p: prof, title: "Teaching workspace", text: "Grade with evidence, find the pattern behind the answers, approve targeted help." },
              { p: sara, title: "Student experience", text: "Think first, work through practice with support, then show what you can do." },
            ].map(({ p, title, text }) => p && (
              <button key={p.id} onClick={() => enter(p.id)} disabled={busy !== null}
                className="group text-left border border-line-strong rounded-lg px-6 py-5 hover:border-accent-strong hover:bg-surface transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-[13px] text-faint">{p.name}</span>
                  <span className="text-faint group-hover:text-accent-ink transition-colors" aria-hidden>→</span>
                </div>
                <div className="text-[18px] text-ink mt-2">{busy === p.id ? "Opening…" : title}</div>
                <div className="text-[14px] text-muted mt-1">{text}</div>
              </button>
            ))}
          </div>
          {people.data && people.data.other_students.length > 0 && (
            <div className="mt-5 flex flex-wrap items-center gap-2 text-[13.5px]">
              <label htmlFor="other" className="text-faint">Or view the class as another student</label>
              <select id="other" value={other} onChange={(e) => setOther(e.target.value)}
                className="bg-surface border border-line-strong rounded h-8 px-2 text-ink max-w-[240px]">
                <option value="">Choose…</option>
                {people.data.other_students.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <button disabled={!other || busy !== null} onClick={() => enter(Number(other))} className="text-accent-ink disabled:text-faint px-1">Enter</button>
            </div>
          )}
          {people.error && <p className="text-brick text-[14px] mt-4">{(people.error as Error).message}</p>}
        </section>
      </main>

      <footer className="w-full max-w-[1200px] mx-auto px-5 sm:px-10 py-6 border-t border-line flex flex-wrap justify-between gap-2 text-[13px] text-faint">
        <span>A space for teaching and learning</span>
        <span>All people, courses and submissions shown are synthetic.</span>
      </footer>
    </div>
  );
}
