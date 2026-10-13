# Industrial Knowledge Intelligence Platform — Master Plan

## Project Overview
**Hackathon:** ET Hackathon  
**Theme:** AI for Industrial Knowledge Intelligence  
**Deadline:** July 7, 2026  
**Start Date:** June 24, 2026  
**Total Days:** ~13 days  
**Team Size:** Solo  

---

## Strategic Approach

Most teams will build a basic RAG chatbot. We build a **full Industrial Intelligence OS**:
- Knowledge Graph (Neo4j) + RAG (Qdrant) hybrid retrieval
- Multi-agent orchestration via LangGraph
- Compliance intelligence layer
- Maintenance RCA agent
- Beautiful, demo-ready Next.js frontend

**Winning differentiator:** Documents + Assets + Failures + Regulations → Single unified graph + conversational AI

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind CSS | Fast, SSR, great DX |
| Backend | FastAPI (Python 3.11) | Async, fast, great for AI |
| Primary AI | Ollama `gpt-oss:120b-cloud` (via local proxy) | Complex reasoning, RCA, compliance — free, cloud-run |
| Fast AI | Ollama `gpt-oss:20b-cloud` (via local proxy) | Entity extraction, classification, summarization — free, cloud-run |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, no API cost |
| Vector DB | Qdrant | Easy Docker, REST API |
| Knowledge Graph | Neo4j Community | Graph queries, visualization |
| OCR | PaddleOCR | Industrial doc accuracy |
| Relational DB | PostgreSQL | Metadata, logs, users |
| File Storage | MinIO (S3-compatible) | Self-hosted, Docker |
| Agent Framework | LangGraph + LangChain | Multi-agent orchestration |
| Containerization | Docker Compose | Single-command startup |
| Graph Viz | react-force-graph | Knowledge graph UI |

---

## Cost & Rate Limit Strategy (Ollama Cloud — Free)

We use **Ollama Cloud** (`https://ollama.com`) — free, hosted, OpenAI-compatible inference. No local model install, no GPU, no paid API key. The free tier has hourly/daily request caps, so we still optimize aggressively:
1. **Tiered model usage:** `gpt-oss:20b` for bulk ops, `gpt-oss:120b` for reasoning
2. **Aggressive caching:** Cache entity extraction results per document hash (SHA256)
3. **Batch processing:** Process documents in batches with delays to stay under free-tier caps
4. **Local embeddings:** Use sentence-transformers instead of any API for embeddings (zero network)
5. **Streaming:** Stream chat responses to improve UX without extra calls
6. **Smart chunking:** Chunk docs to minimize total tokens sent
7. **Provider abstraction:** Single OpenAI-compatible client; swap base URL/key to fail over to a local Ollama or another provider if free tier is exhausted during the demo

**Integration note:** Backend calls the LLM via an OpenAI-compatible client (`openai` Python SDK), NOT the Anthropic SDK. Default endpoint is the **local Ollama daemon** (`http://localhost:11434/v1`), which proxies `*-cloud` models to Ollama's servers — free, no GPU, no API key in our app. From Docker the backend reaches it at `http://host.docker.internal:11434/v1`. Alternative: point directly at `https://ollama.com/v1` with an API key (drop the `-cloud` suffix). Verified working end-to-end on 2026-06-24.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│  Document Upload │ Chat Copilot │ Graph Viz │ Compliance Dash    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST / WebSocket
┌─────────────────────────▼───────────────────────────────────────┐
│                       FASTAPI BACKEND                            │
│  /ingest  │  /chat  │  /graph  │  /compliance  │  /rca          │
└──────┬────────┬──────────┬──────────┬───────────┬──────────────┘
       │        │          │          │           │
  ┌────▼──┐ ┌──▼───┐  ┌───▼───┐ ┌───▼───┐ ┌────▼────┐
  │MinIO  │ │Agent │  │Neo4j  │ │Qdrant │ │Postgres │
  │(Files)│ │Layer │  │(Graph)│ │(Vec)  │ │(Meta)   │
  └───────┘ └──┬───┘  └───────┘ └───────┘ └─────────┘
               │
        ┌──────▼──────┐
        │ LangGraph   │
        │ Agents      │
        ├─────────────┤
        │ Copilot     │
        │ RCA Agent   │
        │ Compliance  │
        │ Ingestion   │
        └──────┬──────┘
               │
        ┌──────────────────┐
        │  Ollama Cloud    │
        │ gpt-oss 120b/20b │
        │ (free, hosted)   │
        └──────────────────┘
```

---

## Module Breakdown

### Module 1: Document Ingestion Pipeline
**Files:** `backend/agents/ingestion_agent.py`, `backend/parsers/`  
**Purpose:** Ingest any industrial document and extract structured knowledge  

Supported formats:
- PDF (text + scanned) → PyPDF2 + PaddleOCR
- Excel/CSV → pandas
- Images (P&IDs, drawings) → PaddleOCR + basic CV
- Email (.eml, .msg) → email library
- Word docs (.docx) → python-docx
- Plain text / Markdown

Extraction outputs:
- Raw text chunks (→ Qdrant)
- Entities: equipment tags, process params, personnel, dates (→ Neo4j)
- Document metadata (→ PostgreSQL)
- File storage (→ MinIO)

### Module 2: Knowledge Graph Builder
**Files:** `backend/graph/neo4j_client.py`, `backend/agents/graph_builder_agent.py`  
**Purpose:** Build and maintain the unified knowledge graph  

Node types: Equipment, Person, Document, Incident, Regulation, Procedure, Location  
Relationship types: MAINTAINS, REFERENCES, CAUSED_BY, REGULATES, LOCATED_AT, RELATES_TO  

### Module 3: Expert Knowledge Copilot
**Files:** `backend/agents/copilot_agent.py`  
**Purpose:** RAG-powered conversational AI for operational queries  

- Hybrid retrieval: Qdrant semantic search + Neo4j graph traversal
- Source citations with document references
- Confidence scoring
- Streaming responses

### Module 4: Maintenance RCA Agent
**Files:** `backend/agents/rca_agent.py`  
**Purpose:** Root cause analysis and predictive maintenance  

- Pulls failure history from Knowledge Graph
- Correlates with maintenance records and sensor data
- Generates structured RCA reports
- Identifies failure patterns

### Module 5: Compliance Intelligence
**Files:** `backend/agents/compliance_agent.py`  
**Purpose:** Map documents to regulations, detect gaps  

Supported regulations: Factory Act, OISD, PESO, Environmental, Quality standards  
- Procedure validation against standards
- Gap detection and risk scoring
- Audit evidence generation
- Automated alerts

### Module 6: Lessons Learned Engine
**Files:** `backend/agents/lessons_agent.py`  
**Purpose:** Learn from incidents, prevent recurrence  

- Pattern discovery across incident reports
- Similar incident detection
- Proactive risk warnings
- Organizational learning repository

---

## Project File Structure

```
ET-hackathon/
├── PLAN.md                          # This file
├── PROGRESS.md                      # Task tracking
├── LOG.md                           # Activity log
├── ARCHITECTURE.md                  # Detailed architecture
├── problem_statement.md             # Original problem
│
├── backend/                         # FastAPI application
│   ├── main.py                      # Entry point
│   ├── config.py                    # Settings (env vars)
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── routers/                     # API routes
│   │   ├── ingest.py
│   │   ├── chat.py
│   │   ├── graph.py
│   │   ├── compliance.py
│   │   └── rca.py
│   │
│   ├── parsers/                     # Document parsers
│   │   ├── pdf_parser.py
│   │   ├── excel_parser.py
│   │   ├── image_parser.py
│   │   ├── email_parser.py
│   │   └── docx_parser.py
│   │
│   ├── agents/                      # LangGraph agents
│   │   ├── ingestion_agent.py
│   │   ├── copilot_agent.py
│   │   ├── rca_agent.py
│   │   ├── compliance_agent.py
│   │   ├── graph_builder_agent.py
│   │   └── lessons_agent.py
│   │
│   ├── graph/                       # Neo4j integration
│   │   ├── neo4j_client.py
│   │   ├── schema.py
│   │   └── queries.py
│   │
│   ├── vector_store/                # Qdrant integration
│   │   ├── qdrant_client.py
│   │   └── embeddings.py
│   │
│   ├── db/                          # PostgreSQL
│   │   ├── database.py
│   │   ├── models.py
│   │   └── crud.py
│   │
│   └── utils/
│       ├── chunker.py
│       ├── entity_extractor.py
│       └── cache.py
│
├── frontend/                        # Next.js application
│   ├── package.json
│   ├── next.config.js
│   ├── Dockerfile
│   ├── tailwind.config.js
│   │
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Landing / Dashboard
│       │   ├── upload/page.tsx      # Document upload
│       │   ├── chat/page.tsx        # Copilot chat
│       │   ├── graph/page.tsx       # Knowledge graph viz
│       │   ├── compliance/page.tsx  # Compliance dashboard
│       │   └── rca/page.tsx         # RCA reports
│       │
│       └── components/
│           ├── ui/                  # shadcn/ui components
│           ├── ChatInterface.tsx
│           ├── DocumentUploader.tsx
│           ├── KnowledgeGraph.tsx
│           ├── ComplianceDashboard.tsx
│           └── RCAReport.tsx
│
├── docker-compose.yml               # Full stack orchestration
├── .env.example                     # Environment variables template
└── sample_data/                     # Demo documents for presentation
    ├── pump_maintenance_report.pdf
    ├── safety_procedure.pdf
    ├── inspection_records.xlsx
    └── incident_report.pdf
```

---

## Sprint Plan (13 Days)

### Phase 1: Foundation (Days 1-2 | June 24-25)
- [ ] Project structure setup
- [ ] Docker Compose with all services
- [ ] FastAPI skeleton with all routers
- [ ] PostgreSQL schema and models
- [ ] Environment configuration
- [ ] Next.js project setup with Tailwind + shadcn/ui

### Phase 2: Data Layer (Days 3-4 | June 26-27)
- [ ] MinIO file storage integration
- [ ] PDF parser (text + OCR path)
- [ ] Excel/CSV parser
- [ ] Image OCR parser (PaddleOCR)
- [ ] Email and DOCX parsers
- [ ] Text chunker utility
- [ ] Qdrant vector store setup + embedding pipeline
- [ ] PostgreSQL document metadata storage

### Phase 3: Knowledge Graph (Days 5-6 | June 28-29)
- [ ] Neo4j client and schema definition
- [ ] Entity extraction agent (Ollama Cloud `gpt-oss:20b`)
- [ ] Graph builder agent
- [ ] Cross-document linking logic
- [ ] Graph query utilities
- [ ] Knowledge Graph API endpoints

### Phase 4: AI Agents (Days 7-9 | June 30 - July 2)
- [ ] Expert Knowledge Copilot (hybrid RAG + graph)
- [ ] Streaming chat endpoint
- [ ] Source citation system
- [ ] Maintenance RCA Agent
- [ ] Compliance Intelligence Agent
- [ ] Lessons Learned Engine

### Phase 5: Frontend (Days 10-11 | July 3-4)
- [ ] Dashboard / landing page
- [ ] Document upload with progress tracking
- [ ] Chat interface with streaming + citations
- [ ] Knowledge Graph visualization (react-force-graph)
- [ ] Compliance dashboard
- [ ] RCA report viewer
- [ ] Mobile responsiveness

### Phase 6: Integration & Polish (Days 12-13 | July 5-7)
- [ ] End-to-end testing
- [ ] Sample data preparation
- [ ] Demo script creation
- [ ] Architecture diagram (for presentation)
- [ ] Performance optimization
- [ ] Bug fixes
- [ ] Demo video recording

---

## API Endpoints

```
POST /api/ingest/upload          # Upload document(s)
GET  /api/ingest/status/{job_id} # Ingestion job status
GET  /api/documents              # List all documents
DELETE /api/documents/{id}       # Delete document

POST /api/chat                   # Send message (streaming)
GET  /api/chat/history/{session} # Chat history

GET  /api/graph/nodes            # Get graph nodes
GET  /api/graph/edges            # Get graph edges
GET  /api/graph/asset/{tag}      # Get asset subgraph
POST /api/graph/search           # Search graph entities

POST /api/rca/analyze            # Run RCA on asset/incident
GET  /api/rca/reports            # List RCA reports
GET  /api/rca/report/{id}        # Get specific report

GET  /api/compliance/scan        # Run compliance scan
GET  /api/compliance/gaps        # Get compliance gaps
GET  /api/compliance/report      # Generate audit report

GET  /api/lessons/patterns       # Get failure patterns
POST /api/lessons/search         # Find similar incidents
```

---

## Environment Variables

```env
# LLM — Ollama cloud models via local proxy (free, OpenAI-compatible)
OLLAMA_API_KEY=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL_FAST=gpt-oss:20b-cloud
LLM_MODEL_SMART=gpt-oss:120b-cloud

# Database
POSTGRES_URL=postgresql://user:password@localhost:5432/industrial_kb
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# Vector Store
QDRANT_URL=http://localhost:6333

# File Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=industrial-docs

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

---

## Demo Flow (For Judges)

1. **Upload** a P&ID drawing + maintenance report + safety procedure
2. **Watch** the system extract entities and build the knowledge graph live
3. **Ask** "Why did Pump P-101 fail last month?" → Get RAG answer with citations
4. **View** the knowledge graph showing P-101's relationships
5. **Run RCA** on Pump P-101 → See structured root cause analysis
6. **Check compliance** → See gaps against OISD standards
7. **Query lessons** → "Show similar incidents to bearing failure" 

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Ollama Cloud free-tier caps hit during demo | Pre-cache demo responses; use gpt-oss:20b for bulk ops; provider abstraction allows failover to local Ollama |
| Neo4j complexity | Start with simple schema, expand incrementally |
| PaddleOCR setup issues | Fallback to Tesseract or pytesseract |
| Time overrun | Phase 5 (frontend) is modular; cut features if needed |
| Docker issues on Windows | Test Docker Desktop settings early |
