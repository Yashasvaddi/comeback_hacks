"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Quote } from "lucide-react";
import { Badge } from "@/components/ui";
import Markdown from "@/components/Markdown";
import { streamChat, Citation } from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  tags?: string[];
}

const SUGGESTIONS = [
  "Why did pump P-101 fail and how was it fixed?",
  "What maintenance was done on P-101?",
  "Which assets show vibration issues?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | undefined>(undefined);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    try {
      await streamChat(
        text,
        (meta) => {
          sessionRef.current = meta.session_id;
          setMessages((m) => {
            const c = [...m];
            const last = c[c.length - 1];
            // Immutable update — mutating would double under React StrictMode.
            c[c.length - 1] = { ...last, citations: meta.citations, confidence: meta.confidence, tags: meta.tags };
            return c;
          });
        },
        (delta) => {
          setMessages((m) => {
            const c = [...m];
            const last = c[c.length - 1];
            c[c.length - 1] = { ...last, content: last.content + delta };
            return c;
          });
          bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        },
        sessionRef.current,
      );
    } catch (e) {
      setMessages((m) => {
        const c = [...m];
        const last = c[c.length - 1];
        c[c.length - 1] = { ...last, content: `⚠️ ${e}` };
        return c;
      });
    } finally {
      setBusy(false);
    }
  }

  const confTone = (c: number) => (c > 0.5 ? "met" : c > 0.3 ? "partial" : "gap");

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-6 py-8">
      <header className="mb-5 border-b border-line pb-4">
        <p className="eyebrow mb-1.5">Expert Knowledge Copilot</p>
        <h1 className="text-2xl font-semibold text-paper">Ask anything about your operations</h1>
        <p className="mt-1 text-[13px] text-muted">Grounded in your documents and the asset graph — every answer cites its sources.</p>
      </header>

      <div className="flex-1 space-y-5 overflow-y-auto pr-1 pb-4">
        {messages.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 space-y-2">
            <p className="eyebrow mb-2">Suggested</p>
            {SUGGESTIONS.map((s, i) => (
              <motion.button
                key={s}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                onClick={() => send(s)}
                className="panel panel-hover block w-full px-4 py-3 text-left text-sm text-paper/85"
              >
                {s}
              </motion.button>
            ))}
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={m.role === "user" ? "flex justify-end" : ""}
            >
              {m.role === "user" ? (
                <div className="max-w-[85%] rounded-lg rounded-br-sm border border-ember/30 bg-ember/[0.08] px-4 py-2.5 text-sm text-paper">
                  {m.content}
                </div>
              ) : (
                <div className="max-w-[90%]">
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ember">Cortex</span>
                    {m.confidence !== undefined && (
                      <Badge tone={confTone(m.confidence)}>{(m.confidence * 100).toFixed(0)}% conf</Badge>
                    )}
                    {m.tags?.map((t) => <Badge key={t} tone="brand">{t}</Badge>)}
                  </div>
                  <div className="panel px-4 py-3" style={{}}>
                    {m.content ? (
                      <Markdown content={m.content} />
                    ) : busy && i === messages.length - 1 ? (
                      <span className="inline-flex gap-1">
                        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-ember" />
                        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-ember [animation-delay:0.2s]" />
                        <span className="h-1.5 w-1.5 animate-blink rounded-full bg-ember [animation-delay:0.4s]" />
                      </span>
                    ) : null}
                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-3 border-t border-line pt-2.5">
                        <p className="eyebrow mb-1.5 flex items-center gap-1"><Quote size={10} /> Sources</p>
                        <div className="flex flex-wrap gap-1.5">
                          {m.citations.map((c, j) => (
                            <span key={j} className="rounded-md border border-line bg-base px-2 py-1 font-mono text-[11px] text-muted">
                              [{j + 1}] {c.title || c.document_id?.slice(0, 8)} · {(c.score * 100).toFixed(0)}%
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2 border-t border-line pt-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about equipment, failures, procedures, compliance…"
          disabled={busy}
          className="panel flex-1 px-4 py-3 text-sm text-paper placeholder:text-faint outline-none focus:border-ember/40"
        />
        <motion.button
          type="submit"
          disabled={busy || !input.trim()}
          whileTap={{ scale: 0.97 }}
          className="flex items-center justify-center rounded-lg bg-ember px-5 text-base shadow-ember disabled:opacity-40"
        >
          <Send size={17} />
        </motion.button>
      </form>
    </div>
  );
}
