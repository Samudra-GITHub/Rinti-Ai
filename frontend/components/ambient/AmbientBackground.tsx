"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { useTheme } from "@/hooks/useTheme";

interface AmbientBackgroundProps {
  /** "hero" is the full scene; "calm" is the quieter version behind a conversation. */
  intensity?: "hero" | "calm";
}

interface Particle {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  phase: number;
  speed: number;
}

function readParticleColor(): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--particle").trim();
  return raw ? raw.replace(/\s+/g, ",") : "130,240,190";
}

/**
 * The scene inside the stage (from the reference): a diagonal light shaft, a
 * floor glow, sparse green particles and grain. It fills its positioned parent
 * and is clipped by the stage's rounded corners. Particles pause while the tab
 * is hidden and draw a single still frame for reduced motion.
 */
export function AmbientBackground({ intensity = "hero" }: AmbientBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const systemReduced = useReducedMotion();
  const { reduceMotion, resolvedTheme } = useTheme();
  const still = Boolean(systemReduced) || reduceMotion;
  const hero = intensity === "hero";

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const color = readParticleColor();
    let width = 0;
    let height = 0;
    let frame = 0;
    let particles: Particle[] = [];
    let last = performance.now();

    const count = () => Math.round(Math.min(64, Math.max(22, (width * height) / 28000)) * (hero ? 1 : 0.45));

    function seed() {
      particles = Array.from({ length: count() }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: 0.5 + Math.random() * 1.3,
        vx: (Math.random() - 0.5) * 5,
        vy: -(2 + Math.random() * 6),
        phase: Math.random() * Math.PI * 2,
        speed: 0.3 + Math.random() * 0.7,
      }));
    }

    function resize() {
      const rect = canvas!.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas!.width = Math.round(width * dpr);
      canvas!.height = Math.round(height * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
      draw(0);
    }

    function draw(t: number) {
      ctx!.clearRect(0, 0, width, height);
      for (const p of particles) {
        const twinkle = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * 0.001 * p.speed + p.phase));
        ctx!.beginPath();
        ctx!.fillStyle = `rgba(${color},${(hero ? 0.55 : 0.3) * twinkle})`;
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fill();
      }
    }

    function tick(now: number) {
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      for (const p of particles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.y < -4) {
          p.y = height + 4;
          p.x = Math.random() * width;
        }
        if (p.x < -4) p.x = width + 4;
        if (p.x > width + 4) p.x = -4;
      }
      draw(now);
      frame = requestAnimationFrame(tick);
    }

    function start() {
      if (still || frame || document.hidden) return;
      last = performance.now();
      frame = requestAnimationFrame(tick);
    }
    function stop() {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
    }
    function onVisibility() {
      if (document.hidden) stop();
      else start();
    }

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    start();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      stop();
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // resolvedTheme: re-read the particle color after a theme change.
  }, [still, hero, resolvedTheme]);

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <div className={hero ? "shaft" : "shaft shaft-calm"} />
      <div className={hero ? "floor-glow" : "floor-glow floor-glow-calm"} />
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      {/* Soft vignette: deep edges, calm center. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 45%, transparent 0%, transparent 40%, rgb(var(--bg) / 0.75) 100%)",
        }}
      />
      <div className="grain" />
    </div>
  );
}
