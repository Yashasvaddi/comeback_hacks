"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Wrench, AlertTriangle, Target, ListChecks, History } from "lucide-react";
import { Panel, PageHeader, Badge, Spinner, Button, Reveal } from "@/components/ui";
import { runRca, listRca } from "@/lib/api";

interface Report {
  asset_tag: string;
  summary: string;
  immediate_cause: string;
  contributing_factors: string[];
  root_causes: string[];
  recommendations: string[];
  similar_incidents: string[];
  confidence: number;
  evidence: { title: string; score: number }[];
}

export default function RcaPage() {
  const [tag, setTag] = useState("P-101");
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<{ id: string; asset_tag: string; confidence: number; summary: string }[]>([]);

  const refresh = () => listRca().then((r) => setHistory(r.reports)).catch(() => {});
  useEffect(() => { refresh(); }, []);

  async function analyze() {
    if (!tag.trim() || busy) return;
    setBusy(true);
    setReport(null);
    try {
      const res = await runRca(tag.trim().toUpperCase());
      setReport(res.report as unknown as Report);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const Section = ({ title, items, icon }: { title: string; items: string[]; icon: React.ReactNode }) =>
    items && items.length > 0 ? (
      <div className="mt-5">
        <p className="mb-2 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">{icon} {title}</p>
        <ul className="space-y-1.5">
          {items.map((it, i) => (
            <motion.li key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="flex gap-2.5 text-sm text-paper/85">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ember" />
              {it}
            </motion.li>
          ))}
        </ul>
      </div>
    ) : null;

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <PageHeader kicker="Maintenance Intelligence" title="Root-Cause Analysis" subtitle="Synthesize asset history and the knowledge graph into a structured RCA — in seconds." />

      <Reveal>
        <div className="flex gap-2">
          <input
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            placeholder="Equipment tag, e.g. P-101"
            className="panel flex-1 px-4 py-3 font-mono text-sm text-paper placeholder:text-faint outline-none focus:border-ember/40"
          />
          <Button onClick={analyze} disabled={busy}><Wrench size={16} /> Analyze</Button>
        </div>
      </Reveal>

      {busy && <div className="mt-8"><Spinner label="Reasoning over evidence with gpt-oss:120b…" /></div>}

      {report && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <Panel hover={false} className="mt-6">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h2 className="font-mono text-2xl font-semibold text-paper">{report.asset_tag}</h2>
              <Badge tone={report.confidence > 0.5 ? "met" : report.confidence > 0.3 ? "partial" : "gap"}>
                {(report.confidence * 100).toFixed(0)}% confidence
              </Badge>
            </div>
            {report.summary && <p className="mt-3 text-sm leading-relaxed text-paper/85">{report.summary}</p>}

            {report.immediate_cause && (
              <div className="mt-5 rounded-lg border border-danger/25 bg-danger/[0.06] p-4">
                <p className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wide text-danger"><AlertTriangle size={13} /> Immediate Cause</p>
                <p className="mt-1 text-sm text-paper">{report.immediate_cause}</p>
              </div>
            )}

            <Section title="Contributing Factors" items={report.contributing_factors} icon={<History size={13} className="text-warn" />} />
            <Section title="Root Causes" items={report.root_causes} icon={<Target size={13} className="text-danger" />} />
            <Section title="Recommendations" items={report.recommendations} icon={<ListChecks size={13} className="text-ok" />} />
            <Section title="Similar Incidents" items={report.similar_incidents} icon={<History size={13} className="text-faint" />} />

            {report.evidence?.length > 0 && (
              <div className="mt-5 border-t border-line pt-3">
                <p className="eyebrow mb-1.5">Evidence</p>
                <div className="flex flex-wrap gap-1.5">
                  {report.evidence.map((e, i) => (
                    <span key={i} className="rounded-md border border-line bg-base px-2 py-1 font-mono text-[11px] text-muted">{e.title} · {(e.score * 100).toFixed(0)}%</span>
                  ))}
                </div>
              </div>
            )}
          </Panel>
        </motion.div>
      )}

      {history.length > 0 && (
        <>
          <p className="eyebrow mb-3 mt-12">Past Reports</p>
          <div className="space-y-2">
            {history.map((h, i) => (
              <Reveal key={h.id} delay={Math.min(i * 0.04, 0.25)}>
                <div className="panel panel-hover flex items-center justify-between px-4 py-3 text-sm">
                  <span className="font-mono font-semibold text-paper">{h.asset_tag}</span>
                  <span className="mx-3 flex-1 truncate text-muted">{h.summary}</span>
                  <Badge tone="brand">{h.confidence}%</Badge>
                </div>
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
