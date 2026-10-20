"use client";

import { useId } from "react";
import { useReducedMotion } from "framer-motion";
import { useTheme } from "@/hooks/useTheme";

// Right-angle traces leaving the node on its left; the right side is the mirror image.
const PATHS = [
  { d: "M 328 32 H 262 V 18 H 44", end: [44, 18], dur: 4.2, begin: 0 },
  { d: "M 328 38 H 292 V 50 H 112", end: [112, 50], dur: 3.6, begin: 1.1 },
  { d: "M 328 26 H 300 V 8 H 232", end: [232, 8], dur: 3.1, begin: 2.0 },
] as const;

function Side({ gradientId, animate }: { gradientId: string; animate: boolean }) {
  return (
    <g>
      {PATHS.map((path) => (
        <g key={path.d}>
          <path d={path.d} fill="none" stroke={`url(#${gradientId})`} strokeWidth="1" strokeLinejoin="round" />
          <circle cx={path.end[0]} cy={path.end[1]} r="2.2" fill="rgb(var(--accent))" opacity="0.8" />
          {animate && (
            <circle r="1.8" fill="rgb(var(--accent))" style={{ filter: "drop-shadow(0 0 4px rgb(var(--accent)))" }}>
              <animateMotion
                dur={`${path.dur}s`}
                begin={`${path.begin}s`}
                repeatCount="indefinite"
                path={path.d}
                keyPoints="0;1"
                keyTimes="0;1"
                calcMode="linear"
              />
            </circle>
          )}
        </g>
      ))}
    </g>
  );
}

interface CircuitTracesProps {
  /** The node the traces lead out of, centered. */
  children: React.ReactNode;
}

/** Decorative circuit traces with travelling pulses, from the reference design. */
export function CircuitTraces({ children }: CircuitTracesProps) {
  const id = useId();
  const gradientId = `trace-${id.replace(/:/g, "")}`;
  const systemReduced = useReducedMotion();
  const { reduceMotion } = useTheme();
  const animate = !systemReduced && !reduceMotion;

  return (
    <div className="relative mx-auto flex h-16 w-full max-w-[720px] items-center justify-center" aria-hidden>
      <svg viewBox="0 0 720 64" className="absolute inset-0 h-full w-full" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1="330" y1="0" x2="20" y2="0">
            <stop offset="0" stopColor="rgb(var(--accent))" stopOpacity="0.65" />
            <stop offset="1" stopColor="rgb(var(--accent))" stopOpacity="0" />
          </linearGradient>
        </defs>
        <Side gradientId={gradientId} animate={animate} />
        <g transform="translate(720 0) scale(-1 1)">
          <Side gradientId={gradientId} animate={animate} />
        </g>
      </svg>
      <div className="relative z-10">{children}</div>
    </div>
  );
}
