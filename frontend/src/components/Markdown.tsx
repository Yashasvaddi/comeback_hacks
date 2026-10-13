"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// gpt-oss sometimes emits citation tokens like 【1†L7-L9】 or 【source】 and
// odd leftover quote artifacts. Normalize them to clean [n] / plain text so the
// copilot reads like a polished answer, not raw model output.
function clean(text: string): string {
  return text
    .replace(/【(\d+)[^】]*】/g, " [$1]") // 【1†L7-L9】 → [1]
    .replace(/【[^】]*】/g, "") // other 【…】 noise
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

export default function Markdown({ content }: { content: string }) {
  return (
    <div className="prose-chat">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{clean(content)}</ReactMarkdown>
    </div>
  );
}
