// The four kinds of evidence in ATHAR, always shown differently so nobody mistakes a suggestion for a fact.
import type { ReactNode } from "react";
import { cx } from "./ui";

export type EvidenceKind = "test" | "ai" | "rules" | "professor" | "verified";

const KIND: Record<EvidenceKind, { label: string; cls: string; help: string }> = {
  test: { label: "Test result", cls: "border-slate/50 text-slate", help: "Deterministic: the code was run against fixed tests." },
  ai: { label: "AI reading", cls: "border-amber/60 border-dashed text-amber", help: "A suggestion from the language model. Not a diagnosis until you confirm it." },
  rules: { label: "Rule reading", cls: "border-amber/60 border-dashed text-amber", help: "A phrase-matching suggestion, not AI. Not a diagnosis until you confirm it." },
  professor: { label: "Your decision", cls: "border-accent-strong text-accent-ink", help: "Recorded by the professor." },
  verified: { label: "Verified outcome", cls: "border-accent-strong bg-accent-wash text-accent-ink", help: "Decided by fixed rules from a new, independent attempt." },
};

export function EvidenceTag({ kind, children }: { kind: EvidenceKind; children?: ReactNode }) {
  const k = KIND[kind];
  return (
    <span title={k.help} className={cx("inline-flex items-center gap-1 h-6 px-2 rounded-[4px] border text-[12px] font-medium whitespace-nowrap", k.cls)}>
      {children ?? k.label}
    </span>
  );
}

export function sourceKind(source: string | null | undefined): EvidenceKind {
  if (source === "ai") return "ai";
  if (source === "baseline") return "rules";
  if (source === "professor") return "professor";
  return "test";
}

/** One-line legend explaining the evidence kinds; place it near any screen that mixes them. */
export function EvidenceLegend({ kinds = ["test", "ai", "professor", "verified"] }: { kinds?: EvidenceKind[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-muted" aria-label="Evidence legend">
      {kinds.map((k) => (
        <span key={k} className="inline-flex items-center gap-2"><EvidenceTag kind={k} /><span className="hidden sm:inline">{KIND[k].help.split(".")[0]}</span></span>
      ))}
    </div>
  );
}
