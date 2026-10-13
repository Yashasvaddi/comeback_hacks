# Activity Log

Chronological log of all work done on the project. Updated after each work session.

---

## 2026-06-24 — Day 1

### Session: Planning & Architecture

**Time:** Start of project  
**Status:** PLANNING COMPLETE

**Work Done:**
- Read and analyzed problem statement thoroughly
- Designed full system architecture (Knowledge Graph + RAG hybrid)
- Chose tech stack with rate-limit-aware AI model tiering
- Created PLAN.md with full sprint breakdown (13 days, 6 phases, 47 tasks)
- Created PROGRESS.md with task tracking per phase
- Created ARCHITECTURE.md with detailed system design
- Designed API endpoint schema
- Designed file/folder structure

**Key Decisions:**
- sentence-transformers for embeddings (saves Claude API calls)
- Claude Haiku for entity extraction (bulk ops, rate limit friendly)
- Claude Sonnet for copilot/RCA/compliance (quality reasoning)
- Qdrant for vector store (Docker-native, REST API)
- MinIO for file storage (S3-compatible)
- LangGraph for agent orchestration

**Next Steps:**
- Start Phase 1: Create project structure and Docker Compose
- Initialize backend FastAPI skeleton
- Initialize frontend Next.js project

**Files Created:**
- `PLAN.md`
- `PROGRESS.md`
- `LOG.md` (this file)
- `ARCHITECTURE.md`

---

## 2026-06-24 — Day 1 (cont.)

### Session: AI Layer Pivot — Paid Claude API → Free Ollama Cloud

**Status:** ARCHITECTURE UPDATED — EXECUTION STARTING

**Decision:** Dropped paid Claude API entirely. Switched to **Ollama Cloud** (`https://ollama.com/v1`) — free, hosted, OpenAI-compatible inference. No local model install, no GPU, no paid key.

**Model tier mapping:**
- Haiku-equivalent (fast/bulk) → `gpt-oss:20b` — entity extraction, classification, summarization
- Sonnet-equivalent (capable) → `gpt-oss:120b` — copilot, RCA, compliance, lessons

**Unchanged:** local sentence-transformers embeddings; SHA256 caching; demo pre-caching.

**Integration:** Backend uses the `openai` Python client pointed at the Ollama Cloud base URL (NOT the Anthropic SDK).

**.env change:** removed `ANTHROPIC_API_KEY`; added `OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `LLM_MODEL_FAST`, `LLM_MODEL_SMART`.

**Docs updated:** PLAN.md, ARCHITECTURE.md, PROGRESS.md, both memory files.

**Next Steps:**
- Begin Phase 1: project structure, docker-compose.yml, FastAPI skeleton, PostgreSQL schema, Next.js init, .env.example

---

## 2026-06-24 — Day 1 (cont.)

### Session: Phase 1 — Foundation (6/6 complete ✅)

**Status:** PHASE 1 COMPLETE

**Work Done:**
- **P1.1** Full project structure: `backend/{routers,parsers,agents,graph,vector_store,db,llm,utils}`, `frontend/src/{app,lib}`, `sample_data/`
- **P1.2** `docker-compose.yml` — postgres, neo4j(+apoc), qdrant, minio, backend, frontend; healthchecks + service-name URL overrides
- **P1.3** FastAPI skeleton — `main.py` (lifespan inits DB, CORS, 5 routers), `config.py` (pydantic-settings), stub routers; `/api/chat` already streams **live from Ollama Cloud** via SSE
- **P1.4** Async SQLAlchemy schema — `documents`, `jobs`, `sessions`, `chat_history`
- **P1.5** Next.js 14 (App Router, TS, Tailwind) scaffolded manually; dashboard landing page; `npm run build` ✓ clean (Next bumped to 14.2.33 for security patch)
- **P1.6** `.env.example` + `config.py` wired to Ollama Cloud env vars

**LLM layer (the pivot, now coded):** `backend/llm/client.py` — `AsyncOpenAI` pointed at `https://ollama.com/v1`, two tiers (`complete()` / `stream()`, FAST=gpt-oss:20b, SMART=gpt-oss:120b), `response_format` JSON support for extraction. Provider-swappable via env.

**Verification:**
- All 11 backend modules pass `py_compile`
- Frontend `npm install` + `npm run build` succeed (4 routes prerendered)

**Not yet verified:** Docker stack (`docker` not on PATH — see Blockers). Live LLM call pending `OLLAMA_API_KEY`.

**Next Steps:**
- Phase 2 (Data Layer): MinIO client, parsers (PDF/Excel/image-OCR/email/DOCX), chunker, Qdrant + sentence-transformers pipeline, ingest router wiring

**Files Created:** `docker-compose.yml`, `.env.example`, `.gitignore`, `backend/{requirements.txt,config.py,main.py,Dockerfile}`, `backend/llm/{client.py,__init__.py}`, `backend/db/{database.py,models.py,__init__.py}`, `backend/routers/{ingest,chat,graph,rca,compliance}.py`, `frontend/{package.json,tsconfig.json,next.config.js,tailwind.config.ts,postcss.config.js,Dockerfile,.eslintrc.json}`, `frontend/src/app/{layout,page}.tsx`, `frontend/src/app/globals.css`, `frontend/src/lib/api.ts`

---

## 2026-06-24 — Day 1 (cont.)

### Session: LLM path verified live + environment confirmed

**Status:** LLM LAYER VERIFIED END-TO-END

**Environment confirmed:**
- Docker Desktop 29.5.3 installed and working
- Local Ollama daemon v0.30.7 on :11434 with cloud remotes enabled

**Decision refined:** Route LLM calls through the **local Ollama daemon** (`http://localhost:11434/v1`) which proxies `*-cloud` models to Ollama's servers — no app API key needed (vs. calling ollama.com directly). Docker backend uses `host.docker.internal:11434`.

**Work Done:**
- Pulled `gpt-oss:20b-cloud` (already present) and `gpt-oss:120b-cloud` (registered as cloud proxy, no weights)
- Reconfigured `config.py`, `.env.example`, `docker-compose.yml` (added `extra_hosts: host-gateway`) for local-proxy endpoint + `-cloud` model names
- Added `complete_json()` + `extract_json()` to `llm/client.py` — strips markdown ```json fences that gpt-oss emits in JSON mode (critical for Phase 3 entity extraction)
- **Verified live against real models:** `complete()` FAST → "FAST OK"; `complete_json()` → clean dict `{equipment:[P-101,V-200], count:2}`; `stream()` SMART → 51 SSE deltas of pump failure modes

**Docs updated:** PLAN.md, ARCHITECTURE.md, PROGRESS.md (decisions + blockers resolved), both memory files.

**Next Steps:**
- Phase 2 (Data Layer): MinIO client, parsers (PDF/Excel/image-OCR/email/DOCX), chunker, Qdrant + sentence-transformers pipeline, wire ingest router

---

## 2026-06-24 — Day 1 (cont.)

### Session: Phase 2 — Data Layer (8/8 complete ✅), verified live

**Status:** PHASE 2 COMPLETE — data pipeline working end-to-end against live Docker stores

**Infrastructure brought up:** `docker compose up` for postgres, neo4j, qdrant, minio — all healthy.

**Work Done:**
- **Parsers** (`parsers/`): `base.py` (extension dispatch + lazy imports + `infer_doc_type` keyword classifier), `pdf_parser.py` (pypdf + OCR fallback), `excel_parser.py` (pandas, sheet/column flattening), `docx_parser.py`, `email_parser.py` (.eml stdlib, .msg optional), `image_parser.py` (PaddleOCR lazy singleton, shared by PDF OCR)
- **Chunker** (`utils/chunker.py`): token-aware sliding window (512/50) on para→sentence→word boundaries with overlap tail
- **Storage** (`storage/minio_client.py`): put/get with unique keys, bucket auto-create
- **Vectors** (`vector_store/`): `embeddings.py` (local all-MiniLM-L6-v2 singleton, 384-dim, normalized), `qdrant_store.py` (collection setup, upsert, cosine search with doc_type filter)
- **DB** (`db/crud.py`): document/job CRUD + finalize; **Ingestion service** (`services/ingestion.py`): parse→chunk→embed→index with staged job updates
- **Ingest router** wired for real: MinIO store → document+job rows → background ingestion task; `/status` + `/documents` endpoints
- **Sample data** (`sample_data/`): pump P-101 maintenance report (.txt), inspection_records.csv

**Bugs found & fixed:**
1. Chunker let a paragraph below the hard 512 threshold exceed a smaller `max_tokens` → made `_split_units` respect `max_tokens` + added word-level `_hard_split`.
2. `.txt` parse branch skipped `infer_doc_type` → now classifies plaintext too.
3. `config.py` resolved `.env` relative to CWD (backend runs from `backend/`) → now resolves project-root `.env` by absolute path.
4. **Postgres port conflict:** host runs native PostgreSQL v13 + v17 on 5432 *and* 5433, intercepting host connections → moved our container to host port **55432** (compose + `.env` + `.env.example` + `config.py`); recreated with fresh volume.

**Verification (live, against Docker stores):**
- Python E2E: MinIO put/get ✓, Postgres rows ✓, ingestion job → complete ✓, Qdrant semantic search returns P-101 doc ✓
- HTTP E2E (uvicorn): `POST /api/ingest/upload` (CSV) → background ingest → `/status` complete → `/documents` shows CSV classified `inspection_record`, 2 chunks ✓
- `/health` confirms LLM provider = local Ollama, both `-cloud` tiers

**Deferred:** PaddleOCR deps (`paddleocr`/`paddlepaddle`) not installed (heavy) — OCR path written but unverified.

**Next Steps:**
- Phase 3 (Knowledge Graph): Neo4j client + constraints, entity extraction prompt (gpt-oss:20b-cloud + `complete_json`), graph builder, cross-doc linking, graph queries, graph router. Add a graph-build stage to `services/ingestion.py`.

---

## 2026-06-24 — Day 1 (cont.)

### Session: Phase 3 — Knowledge Graph (6/6 complete ✅), verified live

**Status:** PHASE 3 COMPLETE — entity extraction → Neo4j graph working against live container

**Work Done:**
- `graph/neo4j_client.py` — async driver lifecycle, uniqueness constraints (7 node types), read/write helpers; schema init wired into `main.py` lifespan
- `graph/entity_extraction.py` — extraction on FAST tier (gpt-oss:20b-cloud) via `complete_json`, SHA256-cached, normalized output; prompt covers equipment/persons/incidents/regulations/procedures/locations/relationships
- `graph/graph_builder.py` — MERGE-based node/rel creation with a relationship-type allowlist (injection-safe); cross-doc linking is implicit via MERGE on natural keys; entities linked to Document via REFERENCED_IN
- `graph/queries.py` — nodes/edges (for viz), asset subgraph, entity search, graph stats
- `routers/graph.py` — `/nodes /edges /stats /asset/{tag} /search`
- `services/ingestion.py` — added a `graph` stage (extract → build) between embedding and finalize; best-effort (won't fail ingestion)

**Verification (live, gpt-oss:20b-cloud + Neo4j container):**
- Extracted from pump P-101 report: 1 equipment, 2 persons, 1 incident, 1 regulation (OISD-STD-105), 3 procedures, 2 locations, 9 relationships
- Built 10 nodes / 19 rels; `graph_stats` shows all node types
- `get_asset_subgraph("P-101")` → LOCATED_AT Unit 3, MAINTAINED_BY Sharma/Mehta, REFERENCES_REGULATION, DESCRIBES_PROCEDURE
- `search_entities("pump")` → Equipment P-101 + Procedure + Incident

**Known refinement (non-blocking):** LLM sometimes uses entity display-name instead of canonical key for relationship endpoints → possible near-duplicate node. Tighten prompt or add canonicalization pass later.

**Next Steps:**
- Phase 4 (AI Agents): hybrid retriever (Qdrant + Neo4j context), Copilot agent + real streaming chat with citations, RCA agent + schema, Compliance agent + report, Lessons engine.

---

## 2026-06-24 — Day 1 (cont.)

### Session: Phase 4 — AI Agents (9/9 complete ✅), all verified live

**Status:** PHASE 4 COMPLETE — the full multi-agent intelligence layer works end-to-end on free Ollama cloud models

**Work Done:**
- `agents/retriever.py` — hybrid retrieval: Qdrant semantic search + equipment-tag detection (regex + graph fallback) + Neo4j asset subgraphs; `build_context_block` renders prompt-ready grounding
- `agents/copilot.py` — Expert Copilot on gpt-oss:120b-cloud, grounded + inline citations, heuristic confidence (top score + graph bonus), streaming
- `routers/chat.py` — SSE protocol (meta event → deltas → done), persists sessions + chat_history to Postgres
- `agents/rca.py` — RCA agent: asset graph history + vector evidence → structured `RCAReport` (Pydantic: immediate/contributing/root causes, recommendations, similar incidents, confidence, evidence)
- `routers/rca.py` + `rca_reports` table — generate/list/fetch persisted reports
- `agents/compliance.py` — OISD/PESO/Factory Act checklist; per-requirement evidence retrieval + LLM verdict (met/partial/gap + risk); overall posture score
- `routers/compliance.py` — scan (cached) + gaps + report
- `agents/lessons.py` + `routers/lessons.py` — similar-incident semantic search + LLM failure-pattern discovery over Incident nodes; registered new lessons router in `main.py`

**Verification (live, gpt-oss:120b-cloud + stores):**
- **Copilot** "Why did P-101 fail?" → confidence 0.67, tags [P-101], citations (pump_P-101 0.571 + inspection_records), grounded streamed answer citing WO-2024-0188 misalignment + lubrication 【1】
- **RCA P-101** → summary + immediate cause (shaft misalignment) + recommendations (alignment interval, vibration monitoring, operator training), confidence 0.72, 3 evidence sources
- **Compliance scan** → 16/100, 6 requirements assessed (2 partial, 4 gaps) each with grounded finding + risk
- **Lessons** → similar-incident search returns P-101 report; pattern discovery → "Bearing degradation / abnormal vibration" with preventive lesson

**Design note:** agents implemented as focused async functions, not LangGraph state machines — simpler and sufficient for these flows. App now exposes 23 routes.

**Next Steps:**
- Phase 5 (Frontend): dashboard, upload, streaming chat UI + citations, graph viz (react-force-graph), compliance dashboard, RCA viewer, lessons page, nav, mobile.

---

## 2026-06-24 — Day 1 (cont.)

### Session: Phase 5 — Frontend (10/10 complete ✅), full stack integrated

**Status:** PHASE 5 COMPLETE — backend + frontend running together, verified end-to-end

**Work Done:**
- Shared kit: `components/ui.tsx` (Card, Badge, Stat, Spinner, PageHeader), `components/Sidebar.tsx` (icon nav, active state, responsive), `app/layout.tsx` (sidebar + main)
- Typed API client `lib/api.ts` — all endpoints + `uploadFiles` (multipart) + `streamChat` (SSE meta/delta parsing)
- Pages: Dashboard (live stats + graph composition bars), Upload (drag-drop + job polling), Chat (streaming + citation cards + confidence), Graph (react-force-graph-2d, color-coded, click→detail panel), RCA (structured sections + history), Compliance (posture score + gap cards), Lessons (pattern cards + similar search)
- Added `react-force-graph-2d`; industrial dark theme via Tailwind config

**Bugs fixed:** two TS errors in graph page (unused `@ts-expect-error`, `onNodeClick` lib typing) → typed callbacks as `any`.

**Verification (live, backend :8000 + frontend :3000):**
- `npm run build` ✓ — all 8 routes compile
- All 7 pages return HTTP 200
- Next→FastAPI proxy works: `/api/ingest/documents` returns real data through the frontend
- Chat SSE streams through the proxy: meta event (citations, confidence 0.47, tags [P-101]) → token deltas

**Next Steps:**
- Phase 6 (Integration & Polish): more sample docs, end-to-end demo run, pre-cache demo responses, architecture diagram, pitch deck, demo script, perf/error hardening, demo video.

---

## 2026-06-24 — Day 1 (cont.)

### Session: UI Redesign — "Cortex" premium glassmorphic experience

**Status:** FRONTEND REDESIGNED — build clean, all routes render

**Why:** Original UI read as a flat grey dashboard — undersold a game-changing product. Goal: make judges fall in love; a glassmorphic, motion-driven, *transparent* experience where the AI pipeline is visible.

**Design language:**
- **Aurora background** — slow-drifting gradient blobs (CSS keyframes, `components/Aurora.tsx`)
- **Glassmorphism** — frosted translucent panels (`.glass` utility, backdrop-blur) — the literal "transparency" the user wanted
- **Neumorphic + glow** shadows; cyan→azure→iris brand gradient
- **Framer Motion** — scroll-reveal (`Reveal`), animated count-up stats (`AnimatedNumber`), staggered list entrances, hover lifts, animated sidebar active-pill (`layoutId`), gradient-sweep buttons
- Fonts via `next/font`: Inter (sans) + Space Grotesk (display)

**New components:** `Aurora`, redesigned `Sidebar` (brand "Cortex", animated pill), full `ui.tsx` kit (GlassCard, GradientButton, GhostButton, Badge, Stat, AnimatedNumber, Reveal, Spinner, Skeleton), and **`Pipeline.tsx`** — the transparency showpiece: uploads visibly animate through Parse → Chunk → Embed → Graph stages with live stage tracking.

**Pages rebuilt (all 7):** hero Dashboard (animated stats + graph bars), Upload (drag-drop + live pipeline viz), Chat (glass bubbles, typing dots, citation chips), Graph (glowing nodes, particle-flow links, animated detail panel), RCA (sectioned report, confidence badge), Compliance (animated radial score gauge), Lessons (pattern cards + search).

**Deps added:** `framer-motion`.

**Verification:** `npm run build` ✓ all 10 routes; live server — all pages HTTP 200, redesign markers present (Cortex, aurora, gradient text). Backend not re-tested this session (Docker Desktop was closed between sessions — restart via START.md; no backend code changed).

**Next Steps:** Phase 6 polish (unchanged). Optional UI follow-ups: page-transition wrapper, graph node-appear animation on first load, light-mode toggle.

---

## 2026-06-24 — Day 1 (cont.)

### Session: UI redesign v2 ("Foundry") + chat markdown fix + Phase 6 rigorous testing

**Status:** UI REDESIGNED (industrial, not AI-generic) · CHAT FIXED · PHASE 6 TESTING PASSED

**Why:** v1 redesign (aurora + purple/cyan glass) read as AI-generated template. User wanted a distinctive, intentional look, plus the copilot was showing raw markdown (`**`, stray `【…】` tokens).

**New design language — "Foundry" (industrial control room):**
- Removed aurora blobs + purple/cyan gradients (the AI tells). New: warm near-black base, **single ember/amber signal accent**, muted semantics (no neon), **engineering dot-grid backdrop**, **JetBrains Mono** for data/labels (technical credibility) + Inter for body.
- Surfaces: solid `.panel` (hairline border, subtle top highlight) instead of frosted glass everywhere.
- Kept tasteful framer-motion (reveals, count-up, sidebar pill, fade-ins) but removed glow-pulsing.
- New `Backdrop.tsx`; rewrote `ui.tsx` (Panel, Button, GhostButton, Badge mono, Stat, Reveal, AnimatedNumber), `Sidebar`, `Pipeline` (ember/ok); all 7 pages restyled.

**Chat markdown fix:** added `react-markdown` + `remark-gfm` via new `Markdown.tsx` with a `clean()` pass that normalizes gpt-oss citation tokens (`【1†L7-L9】` → `[1]`) and strips noise. Copilot answers now render proper bold/lists/headings + tidy source chips.

**Phase 6 rigorous real-world testing (P6.1, P6.2):**
- Built 6 realistic docs sharing assets/people/regs; wiped stores; clean re-ingest via API.
- Graph: 6 Documents, 4 Equipment, 4 Person, 6 Regulation, 8 Procedure, 3 Incident, **82 relationships** — cross-document entity merging confirmed (4 equipment from 6 docs).
- Copilot: cross-doc reasoning verified (pulled 3-month lube interval from OEM manual, not the maintenance report), confidence 0.59–0.77, 6 citations each.
- RCA: P-101 (conf 0.72) and C-150 (conf 0.77) both asset-specific, 8 evidence sources.
- Compliance: 33/100, 4 partial + 2 gaps, nuanced findings from richer evidence.
- Lessons: 2 failure patterns + correct similar-incident ranking.

**Bug found & fixed:** Document/Incident nodes displayed blank labels (keyed by UUID) → added `display_key()` with title fallback in `graph/queries.py`. Verified: all 36 nodes labeled.

**Verification:** frontend `npm run build` clean; all 7 pages HTTP 200; chat SSE + citations through proxy; markdown clean() unit-checked. Backend restarted with fix. App live on :3000 / :8000.

**Next Steps:** Remaining Phase 6 — P6.3 pre-cache demo responses, P6.4 architecture diagram, P6.5 deck, P6.6 demo script, P6.7 perf/error hardening, P6.8 demo video (user).

---

## 2026-06-24 — Day 1 (cont.)

### Session: Chat double-render fix + Phase 6 deliverables

**Status:** PHASE 6 → 5/8 · overall 44/47 (94%)

**Critical bug fixed (from user screenshot):** copilot answers rendered every token **doubled**
("TheThe May May 1212…"), which also broke markdown formatting. Root cause: the streaming
`setMessages` updater **mutated** the existing message object (`content += delta`); React 18
StrictMode double-invokes state updaters in dev → each delta appended twice. Fixed all three
handlers (delta, meta, error) in `app/chat/page.tsx` to update **immutably**
(`c[i] = {...last, content: last.content + delta}`). Frontend build ✓.

**User confirmed** the industrial/ember "Foundry" redesign direction lands.

**Phase 6 deliverables created:**
- `DEMO_SCRIPT.md` (P6.6) — 5–6 min judge-facing walkthrough using our real assets (P-101,
  C-150, V-200), mapped to judging criteria, with pre-demo checklist + free-tier fallback notes.
- `ARCHITECTURE.md` (P6.4) — added **Mermaid** system diagram + ingestion-flow diagram (render on GitHub).
- `PITCH_DECK.md` (P6.5) — 12-slide outline mapped to Innovation/Impact/Technical/Scalability/UX.

**Infra note:** Docker + Ollama were down this session (machine/session restart). Chat fix
verified by build only; user to confirm live via `npm run dev` (hot-reload). Bring the stack
up via START.md.

**Remaining:** P6.3 pre-cache demo responses, P6.7 perf/error hardening, P6.8 demo video (user).

---

_[Future sessions will be logged here]_
