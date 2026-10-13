"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Upload,
  MessageSquare,
  Share2,
  ShieldCheck,
  Wrench,
  Lightbulb,
} from "lucide-react";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Ingest", icon: Upload },
  { href: "/chat", label: "Copilot", icon: MessageSquare },
  { href: "/graph", label: "Knowledge Graph", icon: Share2 },
  { href: "/rca", label: "Root Cause", icon: Wrench },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck },
  { href: "/lessons", label: "Lessons", icon: Lightbulb },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 z-20 flex w-full shrink-0 flex-row gap-1 overflow-x-auto border-b border-line bg-base/80 p-3 backdrop-blur md:h-screen md:w-60 md:flex-col md:gap-0.5 md:overflow-visible md:border-b-0 md:border-r">
      <div className="mb-4 hidden items-center gap-2.5 px-3 py-1.5 md:flex">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-ember/30 bg-ember/10">
          <span className="font-mono text-sm font-bold text-ember">C</span>
        </div>
        <div className="leading-tight">
          <p className="text-[15px] font-semibold text-paper">Cortex</p>
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-faint">Industrial KI</p>
        </div>
      </div>

      {nav.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`group relative flex items-center gap-3 whitespace-nowrap rounded-md px-3 py-2.5 text-sm transition-colors ${
              active ? "text-paper" : "text-muted hover:text-paper"
            }`}
          >
            {active && (
              <motion.span
                layoutId="active-pill"
                className="absolute inset-0 -z-10 rounded-md border border-ember/25 bg-ember/[0.08]"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            {active && <span className="absolute left-0 top-1/2 hidden h-5 w-0.5 -translate-y-1/2 rounded-full bg-ember md:block" />}
            <Icon size={17} className={active ? "text-ember" : "transition-colors group-hover:text-paper"} />
            <span className="font-medium">{item.label}</span>
          </Link>
        );
      })}

      <div className="mt-auto hidden px-3 pb-1 pt-4 md:block">
        <div className="flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-blink rounded-full bg-ok" />
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">Free models · live</span>
        </div>
      </div>
    </aside>
  );
}
