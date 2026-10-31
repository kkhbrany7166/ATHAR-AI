// An open book whose pages leave a trace beneath it: the أثر an education leaves.
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path d="M16 9.5c-2.6-1.6-5.6-2.2-8.5-2v14.2c2.9-.2 5.9.4 8.5 2 2.6-1.6 5.6-2.2 8.5-2V7.5c-2.9-.2-5.9.4-8.5 2Z"
        fill="none" stroke="rgb(var(--accent-ink))" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M16 9.5v14.2" stroke="rgb(var(--accent-ink))" strokeWidth="1.5" />
      <path d="M10 26.2c2.2-.1 4.2.4 6 1.5 1.8-1.1 3.8-1.6 6-1.5" fill="none" stroke="rgb(var(--accent-strong))" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      <span className="flex items-baseline gap-2">
        <span className="font-serif text-[19px] tracking-[0.14em] text-ink">ATHAR</span>
        <span className="font-arabic text-[17px] text-accent-ink leading-none">أثر</span>
      </span>
    </span>
  );
}
