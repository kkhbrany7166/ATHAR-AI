// An open book whose pages leave a trace beneath it: the أثر an education leaves.
export function LogoMark({ size = 26, light = false }: { size?: number; light?: boolean }) {
  const page = light ? "rgb(var(--ink))" : "rgb(var(--accent-ink))";
  const trace = light ? "rgb(var(--ink) / 0.6)" : "rgb(var(--accent-strong))";
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path d="M16 9.5c-2.6-1.6-5.6-2.2-8.5-2v14.2c2.9-.2 5.9.4 8.5 2 2.6-1.6 5.6-2.2 8.5-2V7.5c-2.9-.2-5.9.4-8.5 2Z"
        fill="none" stroke={page} strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 9.5v14.2" stroke={page} strokeWidth="1.6" />
      <path d="M10 26.2c2.2-.1 4.2.4 6 1.5 1.8-1.1 3.8-1.6 6-1.5" fill="none" stroke={trace} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className="w-8 h-8 rounded-md bg-accent/90 grid place-items-center"><LogoMark size={20} light /></span>
      <span className="flex items-baseline gap-2">
        <span className="text-[16px] font-semibold tracking-[0.04em] text-ink">ATHAR</span>
        <span className="font-arabic text-[16px] text-accent-ink leading-none">أثر</span>
      </span>
    </span>
  );
}
