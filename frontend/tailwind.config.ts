import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        panel: "var(--panel)",
        surface: "var(--surface)",
        line: "var(--line)",
        steel: "var(--steel)",
        "steel-fg": "var(--steel-fg)",
        focus: "var(--focus)",
        muted: "var(--muted)",
        danger: "var(--danger)",
        caution: "var(--caution)",
        clear: "var(--clear)",
        neutral: "var(--neutral)",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "-apple-system", "Segoe UI", "sans-serif"],
        mono: [
          "var(--font-plex-mono)",
          "ui-monospace",
          "Cascadia Code",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        xs: ["0.75rem", { lineHeight: "1.1rem" }],
        sm: ["0.8125rem", { lineHeight: "1.25rem" }],
        base: ["0.9375rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.6rem" }],
        xl: ["1.5rem", { lineHeight: "1.9rem" }],
        "2xl": ["2rem", { lineHeight: "2.4rem" }],
      },
      borderRadius: {
        none: "0",
        DEFAULT: "2px",
      },
    },
  },
  plugins: [],
};

export default config;
