import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { UserBrief } from "../lib/types";
import { Wordmark } from "../components/Logo";
import { ErrorState, Loading } from "../components/ui";

const LOOP = ["Assess", "Understand", "Intervene", "Verify"];

export function SignIn() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<number | null>(null);
  const [other, setOther] = useState("");
  const q = useQuery({
    queryKey: ["personas"],
    queryFn: () => api<{ personas: UserBrief[]; other_students: UserBrief[] }>("/api/auth/personas"),
  });

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
    <div className="min-h-screen flex items-center px-4">
      <div className="w-full max-w-[880px] mx-auto grid md:grid-cols-[1.1fr_1fr] gap-12 md:gap-16 py-16">
        <div>
          <Wordmark />
          <h1 className="font-serif text-[34px] leading-[1.15] mt-10 tracking-[-0.01em]">
            Every student understood.<br />Every skill earned.
          </h1>
          <p className="text-muted mt-5 max-w-[46ch]">
            ATHAR helps professors understand each student from the evidence in their work, then act on that
            understanding at scale. AI handles the repetitive work. You make the teaching decisions.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-faint">
            {LOOP.map((s, i) => (
              <span key={s} className="flex items-center gap-2">
                <span className={i < 2 ? "text-accent-ink" : ""}>{s}</span>
                {i < LOOP.length - 1 && <span aria-hidden>→</span>}
              </span>
            ))}
          </div>
        </div>

        <div className="md:pt-16">
          <div className="eyebrow mb-3">Enter the demo as</div>
          {q.isLoading && <Loading label="Loading personas" />}
          {q.error && <ErrorState error={q.error} />}
          {q.data && q.data.personas.length === 0 && (
            <p className="text-muted text-[13px]">No demo data yet. Run <code className="font-mono text-ink">python -m athar.cli reset --grade</code> in <code className="font-mono">backend/</code>.</p>
          )}
          <div className="divide-y divide-line border-y border-line">
            {q.data?.personas.map((p) => (
              <button
                key={p.id}
                onClick={() => enter(p.id)}
                disabled={busy !== null}
                className="w-full text-left py-4 px-1 group flex items-center justify-between gap-4 hover:bg-surface/60 transition-colors"
              >
                <div>
                  <div className="text-[15px] text-ink">{p.name}</div>
                  <div className="text-[12.5px] text-muted mt-0.5">
                    {p.role === "professor" ? "Professor · CS201 Introduction to Programming" : "Student · CS201"}
                  </div>
                </div>
                <span className="text-faint group-hover:text-accent-ink transition-colors text-[13px]">
                  {busy === p.id ? "Opening…" : p.role === "professor" ? "Professor workspace →" : "Student workspace →"}
                </span>
              </button>
            ))}
          </div>
          {q.data && q.data.other_students.length > 0 && (
            <div className="mt-5 flex items-center gap-2">
              <label htmlFor="other" className="text-[12.5px] text-muted shrink-0">Or another student</label>
              <select
                id="other"
                value={other}
                onChange={(e) => setOther(e.target.value)}
                className="flex-1 min-w-0 bg-surface border border-line-strong rounded h-8 px-2 text-[13px] text-ink"
              >
                <option value="">Choose…</option>
                {q.data.other_students.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <button disabled={!other || busy !== null} onClick={() => enter(Number(other))}
                className="text-[13px] text-accent-ink disabled:text-faint px-2">Enter</button>
            </div>
          )}
          <p className="text-2xs text-faint mt-8 leading-5">
            Every person, course and submission in this demo is fictional and generated for demonstration.
            There are no passwords: choosing a persona signs you in as them.
          </p>
        </div>
      </div>
    </div>
  );
}
