"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  FileText,
  Boxes,
  Share2,
  GitBranch,
  MessageSquare,
  Wrench,
  ShieldCheck,
  ArrowUpRight,
} from "lucide-react";
import { Panel, Reveal, Stat, Spinner, Badge } from "@/components/ui";
import { listDocuments, graphStats, DocItem } from "@/lib/api";

export default function Dashboard() {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [nodeCounts, setNodeCounts] = useState<Record<string, number>>({});
  const [rels, setRels] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listDocuments(), graphStats()])
      .then(([d, g]) => {
        setDocs(d.documents);
        setNodeCounts(g.node_counts || {});
        setRels(g.total_relationships || 0);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const totalNodes = Object.values(nodeCounts).reduce((a, b) => a + b, 0);
  const totalChunks = docs.reduce((a, d) => a + (d.chunk_count || 0), 0);

  const actions = [
    { href: "/chat", title: "Ask the Copilot", desc: "Grounded answers, cited sources", icon: MessageSquare },
    { href: "/graph", title: "Explore the Graph", desc: "Assets · incidents · regulations", icon: Share2 },
    { href: "/rca", title: "Run Root-Cause", desc: "Structured failure analysis", icon: Wrench },
    { href: "/compliance", title: "Compliance Scan", desc: "OISD · PESO · Factory Act", icon: ShieldCheck },
  ];

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 md:py-16">
      <Reveal>
        <p className="eyebrow mb-3 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-ember" />
          Industrial Knowledge Intelligence · zero API cost
        </p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight text-paper sm:text-6xl">
          Scattered plant documents,
          <br />
          <span className="text-ember">one reasoning engine.</span>
        </h1>
        <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-muted">
          Cortex ingests maintenance reports, inspections, and procedures — then reasons over them with a
          multi-agent copilot, a root-cause engine, and live compliance intelligence, all on free hosted models.
        </p>
      </Reveal>

      {loading && <div className="mt-12"><Spinner label="Connecting to the intelligence layer…" /></div>}
      {err && (
        <div className="mt-10 rounded-lg border border-danger/30 bg-danger/[0.07] p-4 font-mono text-[13px] text-danger">
          Backend unreachable — start the API (see START.md). {err}
        </div>
      )}

      {!loading && !err && (
        <>
          <div className="mt-12 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Reveal delay={0.04}><Stat label="Documents" value={docs.length} icon={<FileText size={26} />} /></Reveal>
            <Reveal delay={0.08}><Stat label="Text Chunks" value={totalChunks} icon={<Boxes size={26} />} /></Reveal>
            <Reveal delay={0.12}><Stat label="Graph Nodes" value={totalNodes} icon={<Share2 size={26} />} /></Reveal>
            <Reveal delay={0.16}><Stat label="Relationships" value={rels} icon={<GitBranch size={26} />} /></Reveal>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <Reveal delay={0.1}>
              <Panel hover={false} className="h-full">
                <p className="eyebrow mb-4">Knowledge Graph Composition</p>
                {totalNodes === 0 ? (
                  <p className="text-sm text-muted">
                    No graph yet. <Link href="/upload" className="text-ember hover:underline">Ingest a document</Link> to begin.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(nodeCounts).sort((a, b) => b[1] - a[1]).map(([label, count], i) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className="w-28 font-mono text-[12px] text-muted">{label}</span>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                          <motion.div
                            className="h-full rounded-full bg-ember"
                            initial={{ width: 0 }}
                            whileInView={{ width: `${(count / totalNodes) * 100}%` }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.8, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
                          />
                        </div>
                        <span className="w-7 text-right font-mono text-[13px] text-paper">{count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Panel>
            </Reveal>

            <Reveal delay={0.14}>
              <Panel hover={false} className="h-full">
                <p className="eyebrow mb-4">Recent Documents</p>
                {docs.length === 0 ? (
                  <p className="text-sm text-muted">No documents ingested yet.</p>
                ) : (
                  <ul className="space-y-2.5">
                    {docs.slice(0, 6).map((d) => (
                      <li key={d.id} className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2 truncate text-sm text-paper/80">
                          <FileText size={14} className="shrink-0 text-faint" />
                          {d.filename}
                        </span>
                        <Badge tone="brand">{d.doc_type}</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </Reveal>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {actions.map((a, i) => {
              const Icon = a.icon;
              return (
                <Reveal key={a.href} delay={0.04 * i}>
                  <Link href={a.href}>
                    <Panel className="group h-full">
                      <div className="flex items-start justify-between">
                        <Icon className="text-ember" size={22} />
                        <ArrowUpRight size={15} className="text-faint opacity-0 transition-all group-hover:-translate-y-0.5 group-hover:opacity-100" />
                      </div>
                      <h3 className="mt-3 font-semibold text-paper">{a.title}</h3>
                      <p className="mt-1 text-[13px] text-muted">{a.desc}</p>
                    </Panel>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
