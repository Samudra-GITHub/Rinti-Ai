import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
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
        base: {
          black: "#050507",
          void: "#08080c",
          surface: "#0b0b10",
          raised: "#101017",
        },
        purple: {
          50: "#f4f1ff",
          100: "#e6ddff",
          200: "#cbb8ff",
          300: "#ab8dff",
          400: "#8b64f7",
          500: "#7c3aed",
          600: "#6d28d9",
          700: "#5b21b6",
          800: "#4c1d95",
          900: "#33146b",
          glow: "#a78bfa",
        },
        cyan: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
          glow: "#67e8f9",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      backgroundImage: {
        "orb-gradient":
          "radial-gradient(circle at 30% 30%, rgba(167,139,250,0.95), rgba(34,211,238,0.55) 45%, transparent 72%)",
        "aura-gradient":
          "radial-gradient(circle, rgba(124,58,237,0.35), rgba(34,211,238,0.12) 55%, transparent 75%)",
        "panel-gradient":
          "linear-gradient(160deg, rgba(255,255,255,0.07), rgba(255,255,255,0.015))",
        "page-gradient":
          "radial-gradient(circle at 15% -10%, rgba(124,58,237,0.20), transparent 45%), radial-gradient(circle at 85% 10%, rgba(34,211,238,0.14), transparent 40%), radial-gradient(circle at 50% 100%, rgba(124,58,237,0.12), transparent 50%)",
      },
      boxShadow: {
        "glow-purple": "0 0 40px -8px rgba(139,92,246,0.55)",
        "glow-cyan": "0 0 40px -8px rgba(34,211,238,0.5)",
        "glow-soft": "0 0 80px -20px rgba(139,92,246,0.35)",
        "inner-glass": "inset 0 1px 0 0 rgba(255,255,255,0.06)",
      },
      borderRadius: {
        xl2: "1.75rem",
      },
      keyframes: {
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.9" },
          "50%": { transform: "scale(1.06)", opacity: "1" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        "spin-slower": {
          from: { transform: "rotate(360deg)" },
          to: { transform: "rotate(0deg)" },
        },
        "pulse-dot": {
          "0%, 80%, 100%": { opacity: "0.3", transform: "scale(0.85)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        breathe: "breathe 4.5s ease-in-out infinite",
        "spin-slow": "spin-slow 18s linear infinite",
        "spin-slower": "spin-slower 26s linear infinite",
        "pulse-dot": "pulse-dot 1.4s ease-in-out infinite",
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
