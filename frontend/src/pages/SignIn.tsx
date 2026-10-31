import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { misconceptionLabel } from "../lib/labels";
import { useSession } from "../lib/session";
import type { UserBrief } from "../lib/types";
import { LogoMark } from "../components/Logo";

interface Example { available: boolean; student?: string; submission_id?: number; tests_passed?: number; tests_total?: number; quote?: string; flag?: string; reader?: string }

export function SignIn() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const people = useQuery({ queryKey: ["personas"], queryFn: () => api<{ personas: UserBrief[]; other_students: UserBrief[] }>("/api/auth/personas") });
  const ex = useQuery({ queryKey: ["example"], queryFn: () => api<Example>("/api/public/example") });
  const prof = people.data?.personas.find((p) => p.role === "professor");
  const sara = people.data?.personas.find((p) => p.role === "student");

  const enter = async (id: number, to?: string) => {
    setBusy(true);
    try {
      const u = await signIn(id);
      navigate(to ?? (u.role === "professor" ? "/p" : "/s"));
    } finally {
      setBusy(false);
    }
  };
  const e = ex.data;
  const first = e?.student?.split(" ")[0];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full max-w-[1120px] mx-auto px-5 sm:px-10 pt-7 pb-5 flex items-center justify-between">
        <span className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-md bg-accent/90 grid place-items-center"><LogoMark size={22} light /></span>
          <span className="flex items-baseline gap-2">
            <span className="text-[18px] font-semibold tracking-[0.04em]">ATHAR</span>
            <span className="font-arabic text-[19px] text-accent-ink">أثر</span>
          </span>
        </span>
        <span className="hidden sm:block text-[15px] text-muted">Behind every answer is a student.</span>
      </header>

      <main className="flex-1 w-full max-w-[1120px] mx-auto px-5 sm:px-10 grid lg:grid-cols-[1fr_1fr] gap-x-16 gap-y-12 items-center py-10 lg:py-16">
        <div>
          <h1 className="font-serif text-[42px] sm:text-[58px] leading-[1.04] tracking-[-0.015em]">A correct answer isn't always understanding.</h1>
          <p className="text-[19px] leading-relaxed text-muted mt-6 max-w-[34ch]">
            ATHAR reads students' code <em className="not-italic text-ink">and</em> their reasoning, points the professor to what's worth a closer look,
            and checks the result on a new task.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            {prof && <button disabled={busy} onClick={() => enter(prof.id)} className="h-12 px-5 rounded bg-accent text-ink text-[16px] hover:bg-accent-strong">Open the professor view</button>}
            {sara && <button disabled={busy} onClick={() => enter(sara.id)} className="h-12 px-5 rounded border border-line-strong text-ink text-[16px] hover:bg-raised">Open Sara's student view</button>}
          </div>
          <p className="text-[14px] text-faint mt-4">A demo with a fictional course, class and people. No sign-up.</p>
        </div>

        {e?.available ? (
          <figure className="border border-line-strong rounded-lg bg-surface p-6 sm:p-8">
            <div className="text-[14px] text-faint">From the demo class · CS201 recursion assignment</div>
            <p className="font-serif text-[26px] leading-snug mt-3">{first}'s code passes {e.tests_passed} of {e.tests_total} tests. The explanation raises a question.</p>
            <blockquote className="font-serif text-[19px] leading-relaxed text-ink border-l-2 border-amber pl-4 mt-5">“{e.quote}”</blockquote>
            <p className="text-[15px] text-muted mt-5">
              The {e.reader} flagged this as possibly “{misconceptionLabel(e.flag!).toLowerCase()}”. A flag is a question for the professor, not a verdict.
              It can be wrong.
            </p>
            {prof && <button disabled={busy} onClick={() => enter(prof.id, `/p/submissions/${e.submission_id}`)}
              className="mt-6 text-accent-ink text-[16px] hover:underline underline-offset-4">Inspect the evidence →</button>}
          </figure>
        ) : (
          <div className="text-muted">{ex.isLoading ? "Loading an example…" : "No graded class yet. Open the professor view to prepare one."}</div>
        )}
      </main>

      <footer className="w-full max-w-[1120px] mx-auto px-5 sm:px-10 py-6 border-t border-line flex flex-wrap justify-between gap-2 text-[14px] text-faint">
        <span>AI handles repetitive reading. The professor decides. The student does the learning.</span>
        <span>All people and submissions shown are synthetic.</span>
      </footer>
    </div>
  );
}
