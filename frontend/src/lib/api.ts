// Thin client for the FastAPI backend. In the browser we hit same-origin
// /api/* (proxied by next.config rewrites); on the server we use the env URL.
const BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Types ──
export interface DocItem {
  id: string;
  title: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  size_bytes: number;
  created_at: string;
}
export interface Citation {
  document_id: string;
  title: string;
  chunk_index: number;
  score: number;
}
export interface GraphNode {
  id: string;
  label: string;
  key: string;
  props: Record<string, unknown>;
}
export interface GraphEdge {
  source: string;
  target: string;
  rel: string;
}
export interface ComplianceGap {
  framework: string;
  requirement: string;
  status: "met" | "partial" | "gap";
  risk: "high" | "medium" | "low";
  finding: string;
  evidence: string[];
}

// ── Endpoint helpers ──
export const listDocuments = () =>
  apiGet<{ total: number; documents: DocItem[] }>("/api/ingest/documents");

export const jobStatus = (id: string) =>
  apiGet<{ status: string; stage: string | null; progress: number; error: string | null }>(
    `/api/ingest/status/${id}`,
  );

export const graphNodes = () => apiGet<{ nodes: GraphNode[] }>("/api/graph/nodes");
export const graphEdges = () => apiGet<{ edges: GraphEdge[] }>("/api/graph/edges");
export const graphStats = () =>
  apiGet<{ node_counts: Record<string, number>; total_relationships: number }>(
    "/api/graph/stats",
  );
export const assetSubgraph = (tag: string) =>
  apiGet<{ tag: string; found: boolean; equipment: Record<string, unknown> | null; neighbors: { rel: string; label: string; key: string }[] }>(
    `/api/graph/asset/${encodeURIComponent(tag)}`,
  );

export const runCompliance = () =>
  apiGet<{ gaps: ComplianceGap[]; summary: string; score: number }>(
    "/api/compliance/scan",
  );

export const runRca = (asset_tag: string) =>
  apiPost<{ id: string; report: Record<string, unknown> }>("/api/rca/analyze", { asset_tag });
export const listRca = () =>
  apiGet<{ reports: { id: string; asset_tag: string; confidence: number; summary: string; created_at: string }[] }>(
    "/api/rca/reports",
  );

export const lessonsPatterns = () =>
  apiGet<{ patterns: { theme: string; affected_assets: string[]; description: string; lesson: string; occurrences: number }[] }>(
    "/api/lessons/patterns",
  );
export const lessonsSearch = (query: string) =>
  apiPost<{ results: { title: string; text: string; score: number }[] }>(
    "/api/lessons/search",
    { query },
  );

export async function uploadFiles(files: FileList | File[]): Promise<{ results: { filename: string; status: string; job_id?: string; document_id?: string; reason?: string }[] }> {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  const res = await fetch(`/api/ingest/upload`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`upload → ${res.status}`);
  return res.json();
}

// Stream a copilot chat response (SSE). Returns final meta after completion.
export async function streamChat(
  message: string,
  onMeta: (meta: { citations: Citation[]; confidence: number; tags: string[]; session_id: string }) => void,
  onDelta: (text: string) => void,
  sessionId?: string,
): Promise<void> {
  const res = await fetch(`/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.body) throw new Error("No response body for chat stream");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const payload = JSON.parse(trimmed.slice(5).trim());
      if (payload.meta) onMeta(payload.meta);
      if (payload.delta) onDelta(payload.delta);
    }
  }
}
