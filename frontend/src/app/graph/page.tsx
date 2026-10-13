"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { MousePointerClick } from "lucide-react";
import { graphNodes, graphEdges, GraphNode, GraphEdge } from "@/lib/api";
import { Spinner } from "@/components/ui";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const LABEL_COLORS: Record<string, string> = {
  Equipment: "#e8833a",
  Document: "#8a8f98",
  Incident: "#c9564c",
  Person: "#6fa368",
  Regulation: "#d9a441",
  Procedure: "#4f9db0",
  Location: "#7a7268",
};

export default function GraphPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });

  useEffect(() => {
    Promise.all([graphNodes(), graphEdges()])
      .then(([n, e]) => { setNodes(n.nodes); setEdges(e.edges); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const update = () => wrapRef.current && setDims({ w: wrapRef.current.clientWidth, h: wrapRef.current.clientHeight });
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [loading]);

  const data = useMemo(
    () => ({
      nodes: nodes.map((n) => ({ id: n.id, label: n.label, raw: n })),
      links: edges.map((e) => ({ source: e.source, target: e.target, rel: e.rel })),
    }),
    [nodes, edges],
  );

  return (
    <div className="flex h-screen flex-col px-6 py-8">
      <header className="mb-4 border-b border-line pb-4">
        <p className="eyebrow mb-1.5">Unified Knowledge Graph</p>
        <h1 className="text-2xl font-semibold text-paper">Every asset, incident & regulation — connected</h1>
        <p className="mt-1 font-mono text-[12px] text-muted">
          <span className="text-ember">{nodes.length}</span> entities ·{" "}
          <span className="text-petrol">{edges.length}</span> relationships · click a node to inspect
        </p>
      </header>

      <div className="flex flex-1 gap-3 overflow-hidden">
        <div ref={wrapRef} className="panel relative flex-1 overflow-hidden p-0">
          {loading && <div className="p-6"><Spinner label="Rendering the graph…" /></div>}
          {!loading && nodes.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-muted">No graph yet — ingest documents to populate it.</p>
            </div>
          )}
          {!loading && nodes.length > 0 && (
            <ForceGraph2D
              graphData={data}
              width={dims.w}
              height={dims.h}
              backgroundColor="rgba(0,0,0,0)"
              nodeRelSize={5}
              linkColor={() => "rgba(255,255,255,0.10)"}
              linkWidth={1}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={1.4}
              linkDirectionalParticleColor={() => "#e8833a"}
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
                const color = LABEL_COLORS[node.label] || "#7a7268";
                ctx.shadowColor = color;
                ctx.shadowBlur = 6;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, 4.5, 0, 2 * Math.PI);
                ctx.fill();
                ctx.shadowBlur = 0;
                if (scale > 1.3) {
                  ctx.font = `${10.5 / scale}px ui-monospace, monospace`;
                  ctx.fillStyle = "#cbc8c1";
                  ctx.fillText(node.raw.key, node.x + 7, node.y + 3);
                }
              }}
              onNodeClick={(node: any) => setSelected(node.raw)}
            />
          )}
          <div className="absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-md border border-line bg-base/70 px-3 py-2 backdrop-blur">
            {Object.entries(LABEL_COLORS).map(([label, color]) => (
              <span key={label} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wide text-muted">
                <span className="h-2 w-2 rounded-full" style={{ background: color }} />
                {label}
              </span>
            ))}
          </div>
        </div>

        <div className="hidden w-72 shrink-0 overflow-y-auto md:block">
          <AnimatePresence mode="wait">
            {selected ? (
              <motion.div key={selected.id} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 16 }} className="panel p-5">
                <div className="mb-2 flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: LABEL_COLORS[selected.label] }} />
                  <span className="eyebrow">{selected.label}</span>
                </div>
                <h3 className="font-mono text-lg font-semibold text-paper">{selected.key}</h3>
                <dl className="mt-4 space-y-2.5">
                  {Object.entries(selected.props).map(([k, v]) =>
                    v ? (
                      <div key={k}>
                        <dt className="font-mono text-[10px] uppercase tracking-wide text-faint">{k}</dt>
                        <dd className="text-sm text-paper/85">{String(v)}</dd>
                      </div>
                    ) : null,
                  )}
                </dl>
              </motion.div>
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="panel flex flex-col items-center p-8 text-center">
                <MousePointerClick className="mb-3 text-faint" size={26} />
                <p className="text-sm text-muted">Click a node to inspect its properties and connections.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
