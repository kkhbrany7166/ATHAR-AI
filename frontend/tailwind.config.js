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
        sans: ['"Inter"', "system-ui", "sans-serif"],
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        arabic: ['"Noto Naskh Arabic"', "serif"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.02em" }],
      },
      borderRadius: { DEFAULT: "6px", md: "8px", lg: "10px" },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
};
