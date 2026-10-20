import type { Config } from "tailwindcss";

// Every color resolves through a CSS variable defined in globals.css, so one
// class (`text-fg/60`, `bg-surface`, `border-fg/10`, `bg-purple-500/15`) is
// correct in both the dark and the light theme.
const channel = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./common/**/*.{js,ts,jsx,tsx,mdx}",
    "./ui/**/*.{js,ts,jsx,tsx,mdx}",
    "./providers/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        page: channel("page"),
        bg: channel("bg"),
        surface: channel("surface"),
        elevated: channel("elevated"),
        fg: channel("fg"),
        // Single accent family (violet into indigo). The scales flip in the
        // light theme so `text-purple-300` stays readable on a pale surface.
        purple: {
          50: channel("p-50"),
          100: channel("p-100"),
          200: channel("p-200"),
          300: channel("p-300"),
          400: channel("p-400"),
          500: channel("p-500"),
          600: channel("p-600"),
          700: channel("p-700"),
          800: channel("p-800"),
          900: channel("p-900"),
          glow: channel("p-300"),
        },
        cyan: {
          50: channel("c-50"),
          100: channel("c-100"),
          200: channel("c-200"),
          300: channel("c-300"),
          400: channel("c-400"),
          500: channel("c-500"),
          600: channel("c-600"),
          700: channel("c-700"),
          800: channel("c-800"),
          900: channel("c-900"),
          glow: channel("c-300"),
        },
        accent: channel("accent"),
        "on-accent": channel("on-accent"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "orb-gradient":
          "radial-gradient(circle at 30% 30%, rgb(var(--p-300) / 0.95), rgb(var(--c-400) / 0.55) 45%, transparent 72%)",
        "aura-gradient":
          "radial-gradient(circle, rgb(var(--p-500) / 0.35), rgb(var(--c-400) / 0.12) 55%, transparent 75%)",
      },
      boxShadow: {
        "glow-purple": "0 0 36px -10px rgb(var(--p-500) / 0.55)",
        "glow-cyan": "0 0 36px -10px rgb(var(--c-500) / 0.45)",
        "glow-soft": "0 0 70px -24px rgb(var(--p-500) / 0.35)",
        composer:
          "0 1px 0 0 rgb(var(--fg) / 0.04) inset, 0 18px 50px -24px rgb(0 0 0 / var(--shadow-strength))",
      },
      borderRadius: {
        xl2: "1.5rem",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 80%, 100%": { opacity: "0.3", transform: "scale(0.85)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        caret: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.2" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        shimmer: "shimmer 2.5s linear infinite",
        caret: "caret 1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
