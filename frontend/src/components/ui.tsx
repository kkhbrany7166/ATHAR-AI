// ATHAR UI primitives. Small on purpose: typography and spacing carry most of the design.
import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../lib/api";
import type { Judgment, Source } from "../lib/types";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost";
export function Button({ variant = "secondary", className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={cx(
        "inline-flex items-center gap-2 rounded px-3.5 h-9 text-[14px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary" && "bg-accent text-ink hover:bg-accent-strong",
        variant === "secondary" && "border border-line-strong text-ink hover:bg-raised",
        variant === "ghost" && "text-muted hover:text-ink hover:bg-raised",
        className,
      )}
    />
  );
}

export function PageHeader({ eyebrow, title, children, actions }: { eyebrow?: ReactNode; title: ReactNode; children?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-6 pb-7">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
        <h1 className="font-serif text-[30px] leading-[1.15] tracking-[-0.01em]">{title}</h1>
        {children && <div className="mt-3 text-muted max-w-prose">{children}</div>}
      </div>
      {actions && <div className="flex gap-2 shrink-0">{actions}</div>}
    </header>
  );
}

export function Section({ title, aside, children, className }: { title: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx("pt-6 pb-2", className)}>
      <div className="flex items-baseline justify-between gap-4 border-b border-line pb-2.5 mb-4">
        <h2 className="text-[14px] font-semibold tracking-[0.01em] text-ink">{title}</h2>
        {aside && <div className="text-[13px] text-faint">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

type Tone = "neutral" | "accent" | "amber" | "brick" | "slate";
export function Tag({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={cx(
        "inline-flex items-center gap-1 rounded-[4px] px-1.5 h-5 text-2xs font-medium whitespace-nowrap border",
        tone === "neutral" && "border-line-strong text-muted",
        tone === "accent" && "border-accent/50 bg-accent-wash text-accent-ink",
        tone === "amber" && "border-amber/40 bg-amber-wash text-amber",
        tone === "brick" && "border-brick/40 bg-brick-wash text-brick",
        tone === "slate" && "border-slate/40 text-slate",
      )}
    >
      {children}
    </span>
  );
}

export const SynthTag = () => <Tag tone="slate" title="Fictional data generated for the demo">Synthetic</Tag>;

const SOURCE_LABEL: Record<Source, string> = { tests: "Tests", ai: "AI suggestion", professor: "Professor", rules: "Rule" };
export function SourceTag({ source }: { source: Source | null }) {
  if (!source) return null;
  return <Tag tone={source === "ai" ? "amber" : source === "professor" ? "accent" : "neutral"}>{SOURCE_LABEL[source]}</Tag>;
}

const JUDGMENT: Record<Judgment, { label: string; dot: string }> = {
  met: { label: "Met", dot: "bg-accent-strong" },
  partial: { label: "Partial", dot: "bg-amber" },
  not_met: { label: "Not met", dot: "bg-brick" },
  unclear: { label: "Unclear", dot: "bg-faint" },
  ai_unavailable: { label: "Not analysed", dot: "border border-faint" },
  ai_failed: { label: "AI failed", dot: "border border-brick" },
};
export function JudgmentMark({ judgment, compact }: { judgment: Judgment | null; compact?: boolean }) {
  if (!judgment) return <span className="text-faint">—</span>;
  const j = JUDGMENT[judgment];
  return (
    <span className="inline-flex items-center gap-1.5 text-[13.5px] text-muted" title={j.label}>
      <span className={cx("inline-block w-2 h-2 rounded-full", j.dot)} />
      {!compact && j.label}
    </span>
  );
}

export function Callout({ tone = "neutral", title, children }: { tone?: "neutral" | "amber" | "brick" | "accent"; title?: ReactNode; children: ReactNode }) {
  return (
    <div
      className={cx(
        "border-l-2 pl-4 py-1.5 text-[14px]",
        tone === "neutral" && "border-line-strong text-muted",
        tone === "amber" && "border-amber/70 text-muted",
        tone === "brick" && "border-brick/70 text-muted",
        tone === "accent" && "border-accent-strong text-muted",
      )}
    >
      {title && <div className="text-ink font-medium mb-0.5">{title}</div>}
      {children}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="py-16 text-faint text-[14px] flex items-center gap-3" role="status">
      <span className="inline-block w-3 h-3 rounded-full border-2 border-line-strong border-t-accent-ink animate-spin" />
      {label}…
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof ApiError || error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="py-12">
      <Callout tone="brick" title="Could not load this page">{msg}</Callout>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="py-10 text-center">
      <div className="text-ink font-medium">{title}</div>
      {children && <div className="text-muted text-[14px] mt-1 max-w-md mx-auto">{children}</div>}
    </div>
  );
}

export function Crumb({ to, children }: { to: string; children: ReactNode }) {
  return <Link to={to} className="hover:text-muted transition-colors">{children}</Link>;
}

export function CodeBlock({ code, className }: { code: string; className?: string }) {
  const lines = code.replace(/\n$/, "").split("\n");
  return (
    <pre className={cx("font-mono text-[13.5px] leading-[1.65] bg-canvas border border-line rounded-md py-3 overflow-x-auto", className)}>
      {lines.map((l, i) => (
        <div key={i} className="flex">
          <span className="select-none w-10 shrink-0 text-right pr-4 text-faint/70 num">{i + 1}</span>
          <span className="pr-4 whitespace-pre">{l || " "}</span>
        </div>
      ))}
    </pre>
  );
}

/** Highlights verbatim evidence spans inside a student's text. */
export function Highlighted({ text, quotes }: { text: string; quotes: string[] }) {
  const spans: [number, number][] = [];
  const lower = text.toLowerCase();
  for (const q of quotes) {
    const needle = q.toLowerCase().trim();
    if (needle.length < 4) continue;
    const at = lower.indexOf(needle);
    if (at >= 0) spans.push([at, at + needle.length]);
  }
  spans.sort((a, b) => a[0] - b[0]);
  const out: ReactNode[] = [];
  let pos = 0;
  spans.forEach(([s, e], i) => {
    if (s < pos) return;
    out.push(text.slice(pos, s));
    out.push(<mark key={i} className="evidence">{text.slice(s, e)}</mark>);
    pos = e;
  });
  out.push(text.slice(pos));
  return <>{out}</>;
}

export function Meter({ value, total, tone = "accent" }: { value: number; total: number; tone?: "accent" | "brick" | "amber" }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="h-1.5 w-full bg-raised rounded-full overflow-hidden" aria-hidden>
      <div className={cx("h-full rounded-full", tone === "accent" ? "bg-accent-strong" : tone === "brick" ? "bg-brick/80" : "bg-amber/80")} style={{ width: `${pct}%` }} />
    </div>
  );
}

export const CONDITIONS: Record<string, { label: string; help: string }> = {
  assisted: { label: "Assisted practice", help: "AI help is part of the activity. Evidence shows what the student did with support." },
  unsupervised: { label: "Unsupervised assessment", help: "Completed without supervision. It cannot rule out outside help, including AI." },
  supervised: { label: "Supervised assessment", help: "Completed under controlled conditions." },
};
export const KIND: Record<string, string> = { guided_practice: "Guided practice", assessment_check: "Assessment check" };

export function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
