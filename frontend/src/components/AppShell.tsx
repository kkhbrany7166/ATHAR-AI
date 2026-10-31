import { type ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { CourseSummary, Health } from "../lib/types";
import { Wordmark } from "./Logo";
import { cx } from "./ui";

function NavItem({ to, children, end }: { to: string; children: ReactNode; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cx("block rounded px-2.5 py-1.5 text-[13px] transition-colors",
          isActive ? "bg-raised text-ink" : "text-muted hover:text-ink hover:bg-raised/60")}
    >
      {children}
    </NavLink>
  );
}

function AiStatus() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health"), staleTime: 60_000 });
  if (!data) return null;
  const on = data.llm.configured;
  return (
    <div className="text-2xs text-faint leading-4" title={on ? `${data.llm.provider} · ${data.llm.model}` : "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in backend/.env"}>
      <span className={cx("inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle", on ? "bg-accent-strong" : "bg-amber")} />
      {on ? `AI: ${data.llm.model}` : "AI: not configured"}
    </div>
  );
}

export function AppShell() {
  const { user, signOut } = useSession();
  const navigate = useNavigate();
  const isProf = user?.role === "professor";
  const courses = useQuery({
    queryKey: ["prof-courses"],
    queryFn: () => api<CourseSummary[]>("/api/professor/courses"),
    enabled: isProf,
  });

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-[244px] shrink-0 border-b md:border-b-0 md:border-r border-line bg-surface/60 md:min-h-screen flex flex-wrap md:flex-nowrap md:flex-col items-center md:items-stretch">
        <div className="px-5 pt-5 pb-4 flex-1 md:flex-none flex md:block items-center justify-between">
          <Wordmark />
          <div className="eyebrow mt-0 md:mt-5 hidden md:block">{isProf ? "Professor workspace" : "Student workspace"}</div>
        </div>
        <nav className="order-last md:order-none w-full md:w-auto flex md:block gap-1 overflow-x-auto px-3 pb-2 md:pb-0 md:space-y-0.5 md:flex-1">
          {isProf ? (
            <>
              <NavItem to="/p" end>Courses</NavItem>
              {courses.data?.map((c) => (
                <NavItem key={c.id} to={`/p/courses/${c.id}`}>
                  <span className="text-faint mr-1.5">{c.code}</span>{c.title}
                </NavItem>
              ))}
            </>
          ) : (
            <NavItem to="/s" end>My learning</NavItem>
          )}
        </nav>
        <div className="px-5 py-4 md:border-t border-line space-y-3">
          <AiStatus />
          {user && (
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[13px] truncate">{user.name}</div>
                <div className="text-2xs text-faint">{user.is_synthetic ? "Demo persona · fictional" : user.role}</div>
              </div>
              <button
                className="text-2xs text-faint hover:text-ink underline underline-offset-2"
                onClick={() => { signOut(); navigate("/"); }}
              >
                Switch
              </button>
            </div>
          )}
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <div className="max-w-[1120px] mx-auto px-4 sm:px-8 lg:px-12 py-8 lg:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
