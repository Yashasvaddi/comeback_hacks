"use client";

import { motion } from "framer-motion";
import { FileSearch, Scissors, Boxes, Share2, Check } from "lucide-react";

const STEPS = [
  { key: "parsing", label: "Parse", icon: FileSearch },
  { key: "chunking", label: "Chunk", icon: Scissors },
  { key: "embedding", label: "Embed", icon: Boxes },
  { key: "graph", label: "Graph", icon: Share2 },
];

const ORDER = ["pending", "parsing", "chunking", "embedding", "graph", "indexing", "done"];

function stageIndex(stage: string | null | undefined, status: string): number {
  if (status === "complete") return STEPS.length;
  if (!stage) return 0;
  if (stage === "indexing") return STEPS.length;
  return Math.max(0, ORDER.indexOf(stage) - 1);
}

export default function Pipeline({
  stage,
  status,
}: {
  stage: string | null | undefined;
  status: string;
  progress?: number;
}) {
  const current = stageIndex(stage, status);
  const done = status === "complete";

  return (
    <div className="mt-3.5">
      <div className="flex items-center">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          const isDone = i < current || done;
          const isActive = i === current && !done;
          return (
            <div key={step.key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center">
                <motion.div
                  animate={isActive ? { scale: [1, 1.08, 1] } : { scale: 1 }}
                  transition={isActive ? { repeat: Infinity, duration: 1.2 } : {}}
                  className={`flex h-8 w-8 items-center justify-center rounded-md border transition-colors ${
                    isDone
                      ? "border-ok/40 bg-ok/10 text-ok"
                      : isActive
                      ? "border-ember/50 bg-ember/10 text-ember"
                      : "border-line bg-surface text-faint"
                  }`}
                >
                  {isDone ? <Check size={15} /> : <Icon size={15} />}
                </motion.div>
                <span className={`mt-1 font-mono text-[10px] uppercase tracking-wide ${isDone || isActive ? "text-muted" : "text-faint/60"}`}>
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="mx-1.5 mt-[-13px] h-px flex-1 overflow-hidden bg-line">
                  <motion.div
                    className="h-full bg-ok"
                    initial={{ width: 0 }}
                    animate={{ width: i < current || done ? "100%" : isActive ? "55%" : "0%" }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
