/** ATHAR design tokens. Colors resolve to CSS variables defined in src/index.css. */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: v("canvas"),
        surface: v("surface"),
        raised: v("raised"),
        line: v("line"),
        "line-strong": v("line-strong"),
        ink: v("ink"),
        muted: v("muted"),
        faint: v("faint"),
        accent: v("accent"),
        "accent-strong": v("accent-strong"),
        "accent-ink": v("accent-ink"),
        "accent-wash": v("accent-wash"),
        amber: v("amber"),
        "amber-wash": v("amber-wash"),
        brick: v("brick"),
        "brick-wash": v("brick-wash"),
        slate: v("slate"),
      },
      fontFamily: {
        // Plex Sans for the interface, Newsreader for headings and student writing, Plex Mono for code,
        // Plex Sans Arabic so أثر shares the Latin letterforms' structure. See docs/DESIGN-REVIEW.md.
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        serif: ['"Newsreader"', "Georgia", "serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
        arabic: ['"IBM Plex Sans Arabic"', "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.75rem", { lineHeight: "1.05rem", letterSpacing: "0.02em" }],
      },
      borderRadius: { DEFAULT: "6px", md: "8px", lg: "10px" },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
};
