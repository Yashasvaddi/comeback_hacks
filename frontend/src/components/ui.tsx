"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import { motion, useInView, animate } from "framer-motion";

// ── Scroll-reveal ──
export function Reveal({
  children,
  delay = 0,
  y = 16,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ── Panel: solid technical surface ──
export function Panel({
  children,
  className = "",
  hover = true,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div className={`panel ${hover ? "panel-hover hover:-translate-y-px transition-transform" : ""} p-5 ${className}`}>
      {children}
    </div>
  );
}
// Back-compat alias used across pages
export const GlassCard = Panel;

export function PageHeader({ title, subtitle, kicker }: { title: string; subtitle?: string; kicker?: string }) {
  return (
    <Reveal className="mb-8">
      {kicker && <p className="eyebrow mb-2">{kicker}</p>}
      <h1 className="text-3xl font-semibold tracking-tight text-paper sm:text-[2.5rem] sm:leading-[1.1]">
        {title}
      </h1>
      {subtitle && <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">{subtitle}</p>}
    </Reveal>
  );
}

export function AnimatedNumber({ value, className = "" }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const c = animate(0, value, { duration: 1, ease: [0.22, 1, 0.36, 1], onUpdate: (v) => setDisplay(Math.round(v)) });
    return () => c.stop();
  }, [inView, value]);
  return <span ref={ref} className={className}>{display.toLocaleString()}</span>;
}

export function Stat({ label, value, icon }: { label: string; value: number; icon?: ReactNode }) {
  return (
    <Panel className="relative overflow-hidden">
      {icon && <div className="absolute right-4 top-4 text-line">{icon}</div>}
      <p className="eyebrow">{label}</p>
      <p className="mt-2 font-mono text-4xl font-semibold tracking-tight text-paper">
        <AnimatedNumber value={value} />
      </p>
      <span className="absolute bottom-0 left-0 h-px w-full bg-gradient-to-r from-ember/50 to-transparent" />
    </Panel>
  );
}

const TONES: Record<string, string> = {
  high: "bg-danger/10 text-danger border-danger/25",
  medium: "bg-warn/10 text-warn border-warn/25",
  low: "bg-ok/10 text-ok border-ok/25",
  gap: "bg-danger/10 text-danger border-danger/25",
  partial: "bg-warn/10 text-warn border-warn/25",
  met: "bg-ok/10 text-ok border-ok/25",
  brand: "bg-ember/10 text-ember border-ember/25",
};

export function Badge({ children, tone = "" }: { children: ReactNode; tone?: string }) {
  const cls = TONES[tone] || "bg-white/[0.04] text-muted border-line";
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide ${cls}`}>
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-ember px-5 py-3 text-sm font-semibold text-base shadow-ember transition hover:bg-ember/90 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {children}
    </motion.button>
  );
}
// Back-compat alias
export const GradientButton = Button;

export function GhostButton({
  children,
  onClick,
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      whileTap={{ scale: 0.98 }}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border border-line bg-white/[0.03] px-4 py-3 text-sm font-medium text-paper transition hover:border-ember/40 hover:text-paper disabled:opacity-40 ${className}`}
    >
      {children}
    </motion.button>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 font-mono text-[13px] text-muted">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ember border-t-transparent" />
      {label}
    </div>
  );
}
