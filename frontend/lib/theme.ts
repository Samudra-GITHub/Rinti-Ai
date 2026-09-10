export const colors = {
  black: "#050507",
  surface: "#0b0b10",
  purple: {
    400: "#a78bfa",
    500: "#8b5cf6",
    600: "#7c3aed",
  },
  cyan: {
    400: "#67e8f9",
    500: "#22d3ee",
    600: "#0891b2",
  },
} as const;

export const gradients = {
  orb: "radial-gradient(circle at 30% 30%, rgba(167,139,250,0.9), rgba(34,211,238,0.6) 45%, transparent 70%)",
  aura: "radial-gradient(circle, rgba(124,58,237,0.35), rgba(34,211,238,0.15) 55%, transparent 75%)",
  panel: "linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01))",
} as const;

export const shadows = {
  glowPurple: "0 0 40px -8px rgba(139,92,246,0.55)",
  glowCyan: "0 0 40px -8px rgba(34,211,238,0.5)",
  glowSoft: "0 0 80px -20px rgba(139,92,246,0.35)",
} as const;

export const radii = {
  sm: "0.5rem",
  md: "0.875rem",
  lg: "1.25rem",
  xl: "1.75rem",
  full: "9999px",
} as const;
