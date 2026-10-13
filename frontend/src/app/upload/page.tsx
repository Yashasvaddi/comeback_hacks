"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, Check, X } from "lucide-react";
import { Panel, PageHeader, Badge, Reveal } from "@/components/ui";
import Pipeline from "@/components/Pipeline";
import { uploadFiles, jobStatus, listDocuments, DocItem } from "@/lib/api";

interface Tracked {
  filename: string;
  job_id?: string;
  status: string;
  stage?: string | null;
  progress: number;
  reason?: string;
}

export default function UploadPage() {
  const [tracked, setTracked] = useState<Tracked[]>([]);
  const [dragging, setDragging] = useState(false);
  const [docs, setDocs] = useState<DocItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const refreshDocs = () => listDocuments().then((d) => setDocs(d.documents)).catch(() => {});
  useEffect(() => { refreshDocs(); }, []);

  useEffect(() => {
    const active = tracked.filter(
      (t) => t.job_id && !["complete", "failed", "rejected"].includes(t.status),
    );
    if (active.length === 0) return;
    const timer = setInterval(async () => {
      const updates = await Promise.all(
        active.map(async (t) => ({ job_id: t.job_id, ...(await jobStatus(t.job_id!)) })),
      );
      setTracked((prev) =>
        prev.map((t) => {
          const u = updates.find((x) => x.job_id === t.job_id);
          return u ? { ...t, status: u.status, stage: u.stage, progress: u.progress } : t;
        }),
      );
      if (updates.some((u) => u.status === "complete")) refreshDocs();
    }, 1200);
    return () => clearInterval(timer);
  }, [tracked]);

  async function handleFiles(files: FileList | File[]) {
    const res = await uploadFiles(files);
    setTracked((prev) => [
      ...res.results.map((r) => ({
        filename: r.filename,
        job_id: r.job_id,
        status: r.status === "accepted" ? "pending" : "rejected",
        progress: 0,
        reason: r.reason,
      })),
      ...prev,
    ]);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <PageHeader
        kicker="Ingestion Pipeline"
        title="Watch knowledge come alive"
        subtitle="Drop a document and follow it through the pipeline — parsed, chunked, embedded, and woven into the knowledge graph in real time."
      />

      <Reveal>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
          onClick={() => inputRef.current?.click()}
          className={`panel relative flex cursor-pointer flex-col items-center justify-center overflow-hidden border-dashed p-14 transition-colors ${
            dragging ? "border-ember/60 bg-ember/[0.05]" : "panel-hover"
          }`}
        >
          {dragging && <span className="absolute inset-y-0 w-1/3 animate-scan bg-gradient-to-r from-transparent via-ember/10 to-transparent" />}
          <UploadCloud size={42} className="text-ember" strokeWidth={1.6} />
          <p className="mt-4 text-lg font-semibold text-paper">Drag &amp; drop, or click to upload</p>
          <p className="mt-1 font-mono text-[12px] text-faint">PDF · XLSX/CSV · DOCX · EML · PNG/JPG — ≤ 100 MB</p>
          <input ref={inputRef} type="file" multiple hidden onChange={(e) => e.target.files && handleFiles(e.target.files)} />
        </div>
      </Reveal>

      <AnimatePresence>
        {tracked.length > 0 && (
          <div className="mt-5 space-y-3">
            {tracked.map((t, i) => (
              <motion.div key={`${t.filename}-${i}`} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <Panel hover={false}>
                  <div className="flex items-center gap-3">
                    <FileText size={17} className="shrink-0 text-faint" />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-paper">{t.filename}</span>
                    {t.status === "complete" && <span className="flex items-center gap-1 font-mono text-[11px] text-ok"><Check size={14} /> DONE</span>}
                    {(t.status === "failed" || t.status === "rejected") && <span className="flex items-center gap-1 font-mono text-[11px] uppercase text-danger"><X size={14} /> {t.status}</span>}
                    {!["complete", "failed", "rejected"].includes(t.status) && <span className="font-mono text-[11px] text-ember">{t.progress}%</span>}
                  </div>
                  {t.status === "rejected" ? (
                    <p className="mt-1 font-mono text-[12px] text-danger">Rejected: {t.reason}</p>
                  ) : (
                    <Pipeline stage={t.stage} status={t.status} />
                  )}
                </Panel>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>

      <p className="eyebrow mb-3 mt-12">Knowledge Base · {docs.length} documents</p>
      <div className="space-y-2">
        {docs.map((d, i) => (
          <Reveal key={d.id} delay={Math.min(i * 0.03, 0.25)}>
            <div className="panel panel-hover flex items-center justify-between px-4 py-3 text-sm">
              <span className="flex items-center gap-2 truncate text-paper/80">
                <FileText size={14} className="shrink-0 text-faint" /> {d.filename}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-faint">{d.chunk_count} chunks</span>
                <Badge tone="brand">{d.doc_type}</Badge>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
