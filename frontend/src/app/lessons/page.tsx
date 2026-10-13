"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Lightbulb, Search } from "lucide-react";
import { Panel, PageHeader, Badge, Spinner, Button, GhostButton, Reveal } from "@/components/ui";
import { lessonsPatterns, lessonsSearch } from "@/lib/api";

interface Pattern {
  theme: string;
  affected_assets: string[];
  description: string;
  lesson: string;
  occurrences: number;
}

export default function LessonsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loadingPat, setLoadingPat] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ title: string; text: string; score: number }[]>([]);
  const [searching, setSearching] = useState(false);

  async function discover() {
    setLoadingPat(true);
    try { setPatterns((await lessonsPatterns()).patterns); } finally { setLoadingPat(false); }
  }
  async function search() {
    if (!query.trim()) return;
    setSearching(true);
    try { setResults((await lessonsSearch(query.trim())).results); } finally { setSearching(false); }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <PageHeader kicker="Organizational Memory" title="Lessons Learned" subtitle="Recurring failure patterns and similar-incident search across the entire corpus." />

      <Reveal><Button onClick={discover} disabled={loadingPat}><Lightbulb size={16} /> Discover Patterns</Button></Reveal>

      {loadingPat && <div className="mt-8"><Spinner label="Clustering incidents into patterns…" /></div>}

      {patterns.length > 0 && (
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {patterns.map((p, i) => (
            <Reveal key={i} delay={Math.min(i * 0.07, 0.4)}>
              <Panel className="h-full">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-paper">{p.theme}</h3>
                  <Badge tone="brand">{p.occurrences}×</Badge>
                </div>
                {p.affected_assets.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {p.affected_assets.map((a) => <Badge key={a}>{a}</Badge>)}
                  </div>
                )}
                <p className="mt-2.5 text-sm leading-relaxed text-muted">{p.description}</p>
                <div className="mt-3 rounded-lg border border-ember/20 bg-ember/[0.05] p-3">
                  <p className="mb-1 font-mono text-[11px] uppercase tracking-wide text-ember">Lesson</p>
                  <p className="text-sm text-paper/85">{p.lesson}</p>
                </div>
              </Panel>
            </Reveal>
          ))}
        </div>
      )}

      <div className="mt-12">
        <p className="eyebrow mb-3">Find Similar Incidents</p>
        <form onSubmit={(e) => { e.preventDefault(); search(); }} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe a failure, e.g. bearing failure from misalignment"
            className="panel flex-1 px-4 py-3 text-sm text-paper placeholder:text-faint outline-none focus:border-ember/40"
          />
          <GhostButton type="submit" disabled={searching}><Search size={16} /></GhostButton>
        </form>

        {searching && <div className="mt-4"><Spinner /></div>}
        <div className="mt-4 space-y-2">
          {results.map((r, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Panel hover={false}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-paper">{r.title || "document"}</span>
                  <Badge tone="brand">{(r.score * 100).toFixed(0)}% match</Badge>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted">{r.text}…</p>
              </Panel>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
