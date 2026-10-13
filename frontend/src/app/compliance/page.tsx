"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { Panel, PageHeader, Badge, Spinner, Button, Reveal, AnimatedNumber } from "@/components/ui";
import { runCompliance, ComplianceGap } from "@/lib/api";

function ScoreGauge({ score }: { score: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const color = score >= 70 ? "#6fa368" : score >= 40 ? "#d9a441" : "#c9564c";
  return (
    <div className="relative flex h-32 w-32 shrink-0 items-center justify-center">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
        <motion.circle
          cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - (score / 100) * circ }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-3xl font-semibold text-paper"><AnimatedNumber value={score} /></span>
        <span className="font-mono text-[10px] text-faint">/ 100</span>
      </div>
    </div>
  );
}

export default function CompliancePage() {
  const [gaps, setGaps] = useState<ComplianceGap[]>([]);
  const [summary, setSummary] = useState("");
  const [score, setScore] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function scan() {
    setBusy(true);
    try {
      const r = await runCompliance();
      setGaps(r.gaps);
      setSummary(r.summary);
      setScore(r.score);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <PageHeader kicker="Regulatory Intelligence" title="Compliance gap detection" subtitle="Automated assessment against OISD, PESO, and the Factory Act — grounded in your documents." />

      <Reveal><Button onClick={scan} disabled={busy}><ShieldCheck size={16} /> Run Compliance Scan</Button></Reveal>

      {busy && <div className="mt-8"><Spinner label="Auditing requirements against evidence…" /></div>}

      {score !== null && !busy && (
        <>
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
            <Panel hover={false} className="flex flex-col items-center gap-5 sm:flex-row">
              <ScoreGauge score={score} />
              <div>
                <p className="eyebrow mb-1">Compliance Posture</p>
                <p className="text-sm leading-relaxed text-paper/85">{summary}</p>
              </div>
            </Panel>
          </motion.div>

          <div className="mt-4 space-y-3">
            {gaps.map((g, i) => (
              <Reveal key={i} delay={Math.min(i * 0.06, 0.4)}>
                <Panel>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="brand">{g.framework}</Badge>
                    <Badge tone={g.status}>{g.status}</Badge>
                    <Badge tone={g.risk}>{g.risk} risk</Badge>
                  </div>
                  <p className="mt-2.5 font-medium text-paper">{g.requirement}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{g.finding}</p>
                  {g.evidence.length > 0 && (
                    <p className="mt-2 font-mono text-[11px] text-faint">Evidence: {g.evidence.join(" · ")}</p>
                  )}
                </Panel>
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
