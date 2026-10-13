# Progress Tracker

**Last Updated:** 2026-06-24  
**Status:** PHASE 6 IN PROGRESS (5/8) — demo deliverables done; pre-cache, hardening, video remain  
**Overall Progress:** 44 / 47 tasks complete

---

## Legend
- [ ] Not started
- [~] In progress
- [x] Complete
- [!] Blocked

---

## Phase 1: Foundation (June 24-25) — 6/6 complete ✅

- [x] **P1.1** Create full project directory structure
- [x] **P1.2** Write `docker-compose.yml` (PostgreSQL, Neo4j, Qdrant, MinIO + backend/frontend)
- [x] **P1.3** FastAPI skeleton — main.py, config.py, all 5 routers (stubs; chat has live Ollama Cloud SSE)
- [x] **P1.4** PostgreSQL schema: documents, jobs, sessions, chat_history (async SQLAlchemy)
- [x] **P1.5** Next.js 14 init with Tailwind CSS — builds clean (shadcn/ui components added on demand in Phase 5)
- [x] **P1.6** `.env.example` + Ollama-Cloud env wiring in backend config

---

## Phase 2: Data Layer (June 26-27) — 8/8 complete ✅

- [x] **P2.1** MinIO client + file upload service — `storage/minio_client.py` (put/get verified live)
- [x] **P2.2** PDF parser (pypdf text + lazy OCR fallback for scanned pages) — `parsers/pdf_parser.py`
- [x] **P2.3** Excel/CSV parser (pandas) — `parsers/excel_parser.py` (verified: CSV → inspection_record, 10 rows)
- [x] **P2.4** Image OCR parser (PaddleOCR, lazy singleton) — `parsers/image_parser.py` ⚠️ written; paddleocr deps not yet installed (heavy) so OCR path not runtime-tested
- [x] **P2.5** Email (.eml stdlib, .msg optional) + DOCX parsers — `parsers/email_parser.py`, `parsers/docx_parser.py`
- [x] **P2.6** Text chunker (sliding window, 512/50, token-aware, hard-split fallback) — `utils/chunker.py` (bug fixed: respect max_tokens)
- [x] **P2.7** Qdrant client + sentence-transformers (all-MiniLM-L6-v2, local) — `vector_store/{embeddings,qdrant_store}.py` (verified live)
- [x] **P2.8** Ingest router: upload + job status + documents — `routers/ingest.py` + `services/ingestion.py` (verified live over HTTP: upload→ingest→complete)

---

## Phase 3: Knowledge Graph (June 28-29) — 6/6 complete ✅

- [x] **P3.1** Neo4j async client + uniqueness constraints — `graph/neo4j_client.py` (schema init on startup)
- [x] **P3.2** Entity extraction (gpt-oss:20b-cloud + `complete_json`, SHA256-cached) — `graph/entity_extraction.py` (verified: P-101, persons, OISD-STD-105, procedures, incident)
- [x] **P3.3** Graph builder — MERGE nodes + relationships (rel-type allowlist) — `graph/graph_builder.py` (verified: 10 nodes/19 rels)
- [x] **P3.4** Cross-document linking — MERGE on natural keys collapses same entity across docs (built into builder)
- [x] **P3.5** Graph queries — nodes/edges, asset subgraph, entity search, stats — `graph/queries.py` (verified: P-101 subgraph + search)
- [x] **P3.6** Graph API router — `/nodes /edges /stats /asset/{tag} /search` — `routers/graph.py`
- [x] **Integration** — graph-build stage added to `services/ingestion.py`; uploads now populate the graph automatically

---

## Phase 4: AI Agents (June 30 - July 2) — 9/9 complete ✅

- [x] **P4.1** Hybrid retriever (Qdrant + Neo4j, tag detection) — `agents/retriever.py` (verified: P-101 chunks + subgraph)
- [x] **P4.2** Expert Knowledge Copilot — `agents/copilot.py` (grounded, cited; verified confidence 0.67)
- [x] **P4.3** Streaming chat endpoint (SSE: meta→deltas→done) + Postgres history — `routers/chat.py`
- [x] **P4.4** Source citations + confidence scoring — in copilot/chat (verified inline 【1】 + scores)
- [x] **P4.5** Maintenance RCA Agent — graph history + vector evidence → structured RCA — `agents/rca.py` (verified: confidence 0.72)
- [x] **P4.6** RCA report schema (Pydantic) + persisted `rca_reports` table — `agents/rca.py`, `db/models.py`, `routers/rca.py`
- [x] **P4.7** Compliance Agent — OISD/PESO/Factory Act checklist + LLM gap detection — `agents/compliance.py` (verified: 16/100, 4 gaps)
- [x] **P4.8** Compliance report generation + cached scan — `routers/compliance.py`
- [x] **P4.9** Lessons Learned Engine — pattern discovery + similar-incident search — `agents/lessons.py`, `routers/lessons.py` (verified: bearing-vibration pattern)

> Note: agents are implemented as focused async functions (not LangGraph state machines). This is simpler, equally effective for these flows, and avoids LangGraph overhead. Can refactor to LangGraph later if multi-step branching is needed.

---

## Phase 5: Frontend (July 3-4) — 10/10 complete ✅

- [x] **P5.1** Dashboard with live stats (docs, chunks, nodes, rels) + graph composition bars — `app/page.tsx`
- [x] **P5.2** Upload page: drag-drop, multi-file, live job-progress polling — `app/upload/page.tsx`
- [x] **P5.3** Chat UI: streaming SSE, suggestions, citation cards, confidence badge — `app/chat/page.tsx`
- [x] **P5.4** Knowledge Graph viz (react-force-graph-2d, color-coded by label) — `app/graph/page.tsx`
- [x] **P5.5** Graph node detail panel (click → props + legend) — in graph page
- [x] **P5.6** Compliance dashboard (posture score, gap cards, risk/status badges) — `app/compliance/page.tsx`
- [x] **P5.7** RCA viewer (structured sections, confidence, evidence, history) — `app/rca/page.tsx`
- [x] **P5.8** Lessons page (pattern cards + similar-incident search) — `app/lessons/page.tsx`
- [x] **P5.9** Sidebar navigation + layout (lucide icons, active state) — `components/Sidebar.tsx`, `app/layout.tsx`
- [x] **P5.10** Mobile responsiveness (sidebar collapses to top bar, grids stack via `md:` breakpoints)

> Shared UI kit in `components/ui.tsx` (Card, Badge, Stat, Spinner, PageHeader); typed API client in `lib/api.ts`. Industrial dark theme. `npm run build` ✓ all 8 routes.

---

## Phase 6: Integration & Polish (July 5-7) — 5/8 complete

- [x] **P6.1** End-to-end test: upload → parse → graph → chat — **rigorous real-world test passed** (6-doc corpus, all agents, cross-doc linking verified; see LOG 2026-06-24)
- [x] **P6.2** Create sample industrial documents — 6 realistic docs (maintenance, inspection CSV, incident, safety SOP, OEM manual, email thread) sharing assets/people/regulations
- [ ] **P6.3** Pre-cache demo responses to avoid rate limits during live demo *(demo script covers a model-warmup step; formal pre-cache TBD)*
- [x] **P6.4** Architecture diagram — Mermaid system + ingestion-flow diagrams in `ARCHITECTURE.md` (renders on GitHub)
- [x] **P6.5** Presentation deck — `PITCH_DECK.md` (12-slide outline mapped to judging criteria)
- [x] **P6.6** Demo script with exact queries — `DEMO_SCRIPT.md` (5–6 min flow, our real data, fallback notes)
- [ ] **P6.7** Performance tuning + error handling hardening *(in progress: fixed chat StrictMode double-render; graceful backend/empty-corpus states already present)*
- [ ] **P6.8** Demo video recording (screen capture) — **user's task**

### Chat rendering bug (fixed this session)
- **Symptom:** copilot tokens rendered **doubled** ("TheThe May May…"), which also broke markdown.
- **Cause:** streaming `setMessages` updater **mutated** the existing message object (`content += delta`); React 18 StrictMode double-invokes updaters in dev → double append.
- **Fix:** immutable updates (`c[i] = {...last, content: last.content + delta}`) in all three handlers in `app/chat/page.tsx`. Build ✓.

---

## Completion Summary by Phase

| Phase | Tasks | Done | % |
|---|---|---|---|
| Phase 1: Foundation | 6 | 6 | 100% |
| Phase 2: Data Layer | 8 | 8 | 100% |
| Phase 3: Knowledge Graph | 6 | 6 | 100% |
| Phase 4: AI Agents | 9 | 9 | 100% |
| Phase 5: Frontend | 10 | 10 | 100% |
| Phase 6: Polish | 8 | 5 | 63% |
| **TOTAL** | **47** | **44** | **94%** |

---

## Blockers & Issues

- ~~Docker not verified~~ — **RESOLVED 2026-06-24:** Docker Desktop 29.5.3 working. Data stores (postgres/neo4j/qdrant/minio) running; data layer verified live against them.
- ~~`OLLAMA_API_KEY` needed~~ — **RESOLVED 2026-06-24:** Local Ollama daemon proxies `*-cloud` models — no app API key. Both tiers verified end-to-end.
- **Postgres port conflict (RESOLVED 2026-06-24):** host has native PostgreSQL v13 + v17 on 5432 **and** 5433. Moved our container's published port to **55432** (`.env`, `.env.example`, `config.py`, compose). In-Docker networking still uses 5432. ⚠️ Watch for similar conflicts on Neo4j 7474/7687, Qdrant 6333, MinIO 9000 if a native install exists (none seen so far).
- **OCR deps not installed** — `paddleocr`/`paddlepaddle` are heavy and not yet installed locally, so the image/scanned-PDF OCR path (`P2.4`) is written but unverified. Install before testing scanned docs, or rely on the Tesseract fallback noted in the risk register.
- **Graph entity normalization (refinement, not blocking)** — LLM relationship endpoints sometimes use an entity's display name instead of its canonical key (e.g. regulation name vs. code), which can create a near-duplicate node. Tighten the extraction prompt or add a post-extraction canonicalization pass to map relationship endpoints to the keyed entity. Core graph works regardless.
- ~~Document nodes showed empty labels in graph viz~~ — **FIXED 2026-06-24:** added `display_key()` helper in `graph/queries.py` using `title` fallback; all 36 nodes now labeled.
- **Dev-server gotcha (not a code bug)** — rebuilding the frontend (`npm run build`) while a `next start` server is running corrupts `.next` (→ `Cannot find module './NNN.js'`, 500s). Fix: stop the server, `rm -rf .next`, rebuild, restart. Use `npm run dev` during development to avoid this.

---

## Decisions Made

| Date | Decision | Reason |
|---|---|---|
| 2026-06-24 | Use sentence-transformers for embeddings | Avoid any API cost for embeddings; zero network |
| 2026-06-24 | gpt-oss:20b-cloud for entity extraction | Free cloud-run; rate-limit friendly bulk ops |
| 2026-06-24 | gpt-oss:120b-cloud for copilot/RCA/compliance | Free cloud-run; quality reasoning where it matters |
| 2026-06-24 | Switch from paid Claude API to free Ollama cloud models | Zero cost; OpenAI-compatible API |
| 2026-06-24 | Route via LOCAL Ollama daemon (localhost:11434/v1), not ollama.com directly | No app API key; same endpoint serves cloud + local models; user already runs Ollama |
| 2026-06-24 | Added `complete_json()` fence-tolerant JSON parser | gpt-oss wraps JSON-mode output in ```json fences; needed for entity extraction |
| 2026-06-24 | Postgres host port 5432 → 55432 | Native PostgreSQL v13/v17 already occupy 5432/5433 |
| 2026-06-24 | Lazy-import heavy parser deps (PaddleOCR, pandas) | API boots without OCR deps; only pay import cost when format needs it |
| 2026-06-24 | Chunker is token-aware with word-level hard-split | Dense table rows / long sentences must not exceed embed window |
| 2026-06-24 | Qdrant over FAISS | Better REST API, Docker-native, production-ready |
| 2026-06-24 | MinIO over local disk | S3-compatible, scalable, Docker-native |
