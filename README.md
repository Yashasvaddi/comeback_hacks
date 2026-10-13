<div align="center">

# Cortex

**Industrial Knowledge Intelligence Platform**

Turn scattered PDFs, spreadsheets, emails, and scanned forms into a single queryable knowledge graph, with a conversational copilot, automated root-cause analysis, compliance scanning, and a lessons-learned engine on top.

Built for the ET Hackathon 2026 by Team Maybe Coders.

[Quick Start](#quick-start) · [Architecture](#architecture) · [Modules](#modules) · [Tech Stack](#tech-stack) · [Docs](#documentation)

</div>

---

## The Problem

Asset-intensive plants accumulate documentation for decades: OEM manuals, work orders, inspection sheets, incident reports, email threads, scanned handwritten notes. None of these systems talk to each other.

A 2024 McKinsey survey found that professionals in asset-intensive industries spend roughly **35% of their working hours** searching for information that already exists somewhere in the organization. A NASSCOM-EY study of Indian manufacturing and energy plants found the average facility runs across **7 to 12 disconnected document systems**. BIS Research linked this fragmentation to **18-22% of unplanned downtime events** in Indian heavy industry, because maintenance teams make decisions without complete equipment history.

On top of that sits the knowledge cliff: roughly a quarter of India's experienced industrial engineers will retire within the next decade, taking undocumented operational judgment with them.

Cortex is a working answer to that gap. It ingests whatever documents a plant already has, builds a knowledge graph out of the entities inside them, and gives operators a single interface to ask questions, investigate failures, check compliance, and surface patterns across incidents that no single document would reveal on its own.

## What Makes This Different From a RAG Chatbot

Most teams solving this kind of problem ship a document chatbot: embed some PDFs, do a similarity search, hand the top chunks to an LLM. That answers "what does this document say" reasonably well. It falls apart on questions that span multiple documents, like:

> Who else maintains equipment that had an incident in the same unit as pump P-101?

That answer requires knowing that P-101 is linked to a location, that the location has other equipment, that some of that equipment had incidents, and who investigated them. No single chunk of text contains that chain of facts. Cortex answers it because every document that gets ingested also has its entities merged into a Neo4j graph, so the same physical asset (say, `P-101`) is one graph node no matter how many separate documents mention it.

Every query the copilot handles runs two retrieval paths at once:

- **Semantic search** over document chunks (Qdrant, local embeddings)
- **Graph traversal** over the entity relationship structure (Neo4j)

The two results are merged before being handed to the LLM, so answers are grounded in both what the documents say and how the entities in them are connected.

## Modules

| Module | What it does |
|---|---|
| **Document Ingestion** | Parses PDF, Excel/CSV, DOCX, `.eml` email threads, and scanned images (OCR). Classifies document type automatically, chunks and embeds text, extracts structured entities, and merges them into the graph. |
| **Knowledge Graph** | Neo4j graph with 7 entity types (Equipment, Document, Incident, Regulation, Person, Location, Procedure) and 10 relationship types. Cross-document entity deduplication via MERGE on natural keys, so the same asset tag is always the same node. |
| **Expert Copilot** | Conversational assistant with hybrid retrieval (Qdrant + graph context), streamed answers, source citations, and a confidence score. |
| **Maintenance RCA** | Given an equipment tag, produces a structured root cause analysis — immediate cause, contributing factors, root causes, supporting evidence, and recommendations — synthesized across every document that mentions that asset. |
| **Compliance Intelligence** | Scans the full corpus against a checklist mapped to real Indian regulatory frameworks (OISD standards, PESO, Factory Act 1948) and reports MET / PARTIAL / GAP status with evidence and risk level per item. |
| **Lessons Learned Engine** | Discovers recurring failure patterns across ingested incidents and finds semantically similar past incidents for a described failure mode. |

## Architecture

```
                          ┌─────────────────────┐
                          │   Next.js Frontend    │
                          │  Chat · Graph · RCA   │
                          │  Compliance · Upload  │
                          └──────────┬───────────┘
                                     │ HTTP / SSE
                          ┌──────────▼───────────┐
                          │   FastAPI Backend     │
                          │  Routers · Agents     │
                          │  Parsers · Chunker    │
                          └─┬──────┬──────┬───────┘
                            │      │      │
              ┌─────────────┘      │      └─────────────┐
              ▼                    ▼                     ▼
      ┌───────────────┐   ┌───────────────┐    ┌────────────────┐
      │   PostgreSQL   │   │     Neo4j     │    │     Qdrant      │
      │ docs · jobs ·  │   │ Knowledge     │    │ Vector store     │
      │ chat sessions  │   │ Graph         │    │ 384-dim chunks   │
      └───────────────┘   └───────────────┘    └────────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │   Ollama Daemon    │
                   │  gpt-oss:20b-cloud │  ← bulk / structured extraction
                   │  gpt-oss:120b-cloud│  ← reasoning / streamed answers
                   └──────────────────┘
```

Five detailed diagrams (system architecture, ingestion pipeline, graph schema, agent routing, and the full RAG retrieval sequence) are provided as Eraser.io DSL files in [`eraser_diagrams/`](eraser_diagrams/) — paste any of them into [app.eraser.io](https://app.eraser.io) to render.

### Ingestion pipeline

```
Upload → Parse → Infer Type → Chunk (512 tok / 50 overlap) → Embed (local)
       → Qdrant upsert → Entity Extraction (SHA256-cached) → Graph MERGE → Done
```

The graph-build stage is best-effort: if Neo4j is briefly unreachable or extraction fails on a chunk, the document still finishes ingesting and remains searchable. Nothing blocks on the graph.

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS | App Router, streaming-friendly, fast iteration |
| Backend | FastAPI, async SQLAlchemy | Native async, first-class SSE streaming support |
| LLM | Ollama cloud models (`gpt-oss:20b-cloud`, `gpt-oss:120b-cloud`) via the OpenAI SDK | Full-quality inference with zero API cost and no local GPU requirement |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Runs locally, 384-dim, no network call per chunk |
| Knowledge Graph | Neo4j 5 | Native graph traversal for cross-document entity relationships |
| Vector Store | Qdrant | Fast local semantic search over chunk embeddings |
| Relational Store | PostgreSQL 16 | Document metadata, ingestion jobs, chat session history |
| Object Storage | MinIO | S3-compatible storage for raw uploaded files |
| Orchestration | Docker Compose | Single command to bring up all seven services |

The entire AI layer runs on **free Ollama cloud models** proxied through a local Ollama daemon. There is no Anthropic, OpenAI, or other paid API key anywhere in this stack.

## Quick Start

### Prerequisites

- Docker Desktop
- [Ollama](https://ollama.com) installed and signed in (`ollama signin`)
- The two cloud models pulled once:
  ```bash
  ollama pull gpt-oss:20b-cloud
  ollama pull gpt-oss:120b-cloud
  ```

### Run it

```bash
git clone https://github.com/Niteshd05/ET_Hackathon_Team_maybe_coders.git
cd ET_Hackathon_Team_maybe_coders
cp .env.example .env      # defaults work out of the box
docker compose up -d
```

Then open:

| Service | URL |
|---|---|
| App | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |

First run pulls images and builds containers (3-5 minutes). Watch `docker compose logs -f backend` for `Application startup complete` before using the UI.

Full step-by-step instructions, including how to inspect the Postgres/Neo4j/Qdrant data directly, live in [`docs/START.md`](docs/START.md).

### Try it with real data

`sample_data/` ships with six cross-linked synthetic documents (a pump maintenance report, an OEM manual excerpt, a compressor incident report, a hot-work SOP, an inspection email thread, and a sensor CSV) plus two real-world PDFs in `sample_data/real_world/` — a 73-page Grundfos pump manual and a real CSB incident investigation report. Upload them all and ask the copilot something like:

> Why did pump P-101 fail and how was it fixed?

The answer draws from three separate documents in one response, with citations.

Expected answers for every sample query are documented in [`QNA_GROUND_TRUTH.md`](QNA_GROUND_TRUTH.md) and [`QNA_GRUNDFOS_MANUAL.md`](QNA_GRUNDFOS_MANUAL.md) so you can verify retrieval quality without guessing at what "correct" looks like.

## Repository Layout

```
backend/
  agents/       copilot.py · rca.py · compliance.py · lessons.py · retriever.py
  db/           SQLAlchemy models, async session, migrations
  graph/        Neo4j client, entity extraction, graph builder, read queries
  llm/          OpenAI-SDK client pointed at the local Ollama daemon
  parsers/      pdf · excel · docx · email · image (OCR)
  routers/      chat · ingest · graph · documents · compliance · lessons
  services/     ingestion.py — orchestrates the full pipeline
  utils/        chunker.py — token-aware sliding-window chunking
  vector_store/ qdrant.py
frontend/
  src/app/      dashboard · chat · upload · graph · documents · compliance · rca · lessons
  src/components/  Markdown, Pipeline (animated ingestion stages), Backdrop, UI primitives
  src/lib/      typed API client (streamChat, fetchGraph, runRCA, ...)
docs/           ARCHITECTURE.md · START.md · DEMO_SCRIPT.md · PITCH_DECK.md · PLAN.md · PROGRESS.md
sample_data/    curated cross-linked test corpus + real-world PDFs
eraser_diagrams/ 5 architecture diagrams (Eraser.io DSL)
docker-compose.yml
CORTEX_TECHNICAL_REPORT.pdf   full technical writeup
```

## Documentation

| Doc | Contents |
|---|---|
| [`docs/START.md`](docs/START.md) | Every command needed to start the stack, plus how to browse Postgres/Neo4j/Qdrant directly |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Full system design, data flow, and design rationale |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Judge-facing walkthrough with exact demo queries |
| [`docs/PITCH_DECK.md`](docs/PITCH_DECK.md) | 12-slide pitch outline |
| [`docs/PLAN.md`](docs/PLAN.md) / [`docs/PROGRESS.md`](docs/PROGRESS.md) | Sprint plan and build log |
| [`CORTEX_TECHNICAL_REPORT.pdf`](CORTEX_TECHNICAL_REPORT.pdf) | Full technical report covering every module, schema, and design decision |
| [`QNA_GROUND_TRUTH.md`](QNA_GROUND_TRUTH.md) | Expected answers for the sample document set |
| [`QNA_GRUNDFOS_MANUAL.md`](QNA_GRUNDFOS_MANUAL.md) | Expected answers for the real-world Grundfos OEM manual |


