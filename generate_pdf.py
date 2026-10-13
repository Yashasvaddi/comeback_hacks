"""
Generate CORTEX_TECHNICAL_REPORT.pdf using ReportLab.
Run from the project root: python generate_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
import datetime
import os

# ─── Colors ──────────────────────────────────────────────────────────────────
EMBER     = colors.HexColor("#e8833a")
COAL      = colors.HexColor("#1a1a1a")
DARK_GREY = colors.HexColor("#2d2d2d")
MID_GREY  = colors.HexColor("#555555")
LIGHT_BG  = colors.HexColor("#f5f3f0")
RULE      = colors.HexColor("#d0ccc8")
CODE_BG   = colors.HexColor("#f0ede9")
WHITE     = colors.white
TABLE_HDR = colors.HexColor("#2d2d2d")
TABLE_ALT = colors.HexColor("#f9f7f5")

W, H = A4  # 595.27 x 841.89 pts

# ─── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def s(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE   = s("Title_",   fontName="Helvetica-Bold",   fontSize=32, leading=38,  textColor=COAL,     spaceAfter=6,  alignment=TA_LEFT)
SUBTITLE= s("Sub_",     fontName="Helvetica",         fontSize=14, leading=18,  textColor=MID_GREY, spaceAfter=4,  alignment=TA_LEFT)
EYEBROW = s("Eyebrow_", fontName="Helvetica",         fontSize=8,  leading=10,  textColor=EMBER,    spaceAfter=4,  alignment=TA_LEFT, letterSpacing=2)
H1      = s("H1_",      fontName="Helvetica-Bold",   fontSize=18, leading=22,  textColor=COAL,     spaceBefore=18, spaceAfter=6)
H2      = s("H2_",      fontName="Helvetica-Bold",   fontSize=13, leading=16,  textColor=DARK_GREY,spaceBefore=12, spaceAfter=4)
H3      = s("H3_",      fontName="Helvetica-Bold",   fontSize=11, leading=13,  textColor=MID_GREY, spaceBefore=8,  spaceAfter=3)
BODY    = s("Body_",    fontName="Helvetica",         fontSize=9.5, leading=14, textColor=DARK_GREY,spaceAfter=6,  alignment=TA_JUSTIFY)
BODY_SM = s("BodySm_",  fontName="Helvetica",         fontSize=8.5, leading=12, textColor=MID_GREY, spaceAfter=4)
CODE    = s("Code_",    fontName="Courier",           fontSize=7.5, leading=10, textColor=COAL,     spaceAfter=4,  backColor=CODE_BG, leftIndent=6, rightIndent=6)
BULLET  = s("Bullet_",  fontName="Helvetica",         fontSize=9,   leading=13, textColor=DARK_GREY,spaceAfter=2,  leftIndent=14, firstLineIndent=-10)
CAPTION = s("Caption_", fontName="Helvetica-Oblique", fontSize=8,   leading=10, textColor=MID_GREY, spaceAfter=6,  alignment=TA_CENTER)
LABEL   = s("Label_",   fontName="Helvetica-Bold",   fontSize=8,   leading=10, textColor=MID_GREY, spaceAfter=2)
META    = s("Meta_",    fontName="Helvetica",         fontSize=8,   leading=11, textColor=MID_GREY, spaceAfter=2)
COVER_BIG= s("CoverBig_",fontName="Helvetica-Bold",  fontSize=52, leading=58,  textColor=COAL,     spaceAfter=0,  alignment=TA_LEFT)
COVER_SUB= s("CoverSub_",fontName="Helvetica",       fontSize=15, leading=20,  textColor=MID_GREY, spaceAfter=0,  alignment=TA_LEFT)

def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", BULLET)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8, spaceBefore=4)

def code_block(text):
    lines = []
    for line in text.strip().split("\n"):
        lines.append(Paragraph(line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"), CODE))
    return lines

def tbl(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("BACKGROUND",  (0, 0), (-1, 0 if header else -1), TABLE_HDR if header else WHITE),
        ("TEXTCOLOR",   (0, 0), (-1, 0 if header else -1), WHITE if header else COAL),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("LEADING",     (0, 0), (-1, -1), 11),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, TABLE_ALT]),
        ("GRID",        (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",(0, 0), (-1, -1), 7),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]
    t.setStyle(TableStyle(cmds))
    return t

# ─── Page numbering ───────────────────────────────────────────────────────────
def add_page_number(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(MID_GREY)
    page_num = canvas_obj.getPageNumber()
    if page_num > 1:
        canvas_obj.drawString(2*cm, 1.2*cm, "CORTEX — Industrial Knowledge Intelligence Platform")
        canvas_obj.drawRightString(W - 2*cm, 1.2*cm, f"Page {page_num}")
        canvas_obj.setStrokeColor(RULE)
        canvas_obj.setLineWidth(0.4)
        canvas_obj.line(2*cm, 1.5*cm, W - 2*cm, 1.5*cm)
    canvas_obj.restoreState()

# ─── Build document ───────────────────────────────────────────────────────────
def build():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CORTEX_TECHNICAL_REPORT.pdf")
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.2*cm, bottomMargin=2.5*cm,
        title="CORTEX Technical Report",
        author="Cortex Engineering Team",
        subject="Industrial Knowledge Intelligence Platform",
    )

    story = []
    TW = W - 4.4*cm   # text width

    # =========================================================
    # COVER
    # =========================================================
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("CORTEX", COVER_BIG))
    story.append(Spacer(1, 0.3*cm))
    bar_data = [[""]]
    bar = Table(bar_data, colWidths=[TW], rowHeights=[4])
    bar.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,-1), EMBER), ("LINEABOVE",(0,0),(-1,-1),0,EMBER)]))
    story.append(bar)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Industrial Knowledge Intelligence Platform", COVER_SUB))
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Technical Architecture and Implementation Report", SUBTITLE))
    story.append(Spacer(1, 4*cm))

    cover_meta = [
        ["Project",   "Cortex"],
        ["Version",   "1.0 — ET Hackathon Build"],
        ["Date",      datetime.date.today().strftime("%B %d, %Y")],
        ["Stack",     "FastAPI · Next.js · Neo4j · Qdrant · Ollama · PostgreSQL"],
        ["Modules",   "Ingestion · Copilot · RCA · Compliance · Lessons Learned"],
    ]
    meta_tbl = Table(cover_meta, colWidths=[3.5*cm, TW - 3.5*cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (1,0),(1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0),(-1,-1), 8.5),
        ("LEADING",   (0,0),(-1,-1), 12),
        ("TEXTCOLOR", (0,0),(0,-1), EMBER),
        ("TEXTCOLOR", (1,0),(1,-1), DARK_GREY),
        ("TOPPADDING",(0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW", (0,0),(-1,-2), 0.3, RULE),
        ("LEFTPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())

    # =========================================================
    # 1. EXECUTIVE SUMMARY
    # =========================================================
    story.append(Paragraph("EXECUTIVE SUMMARY", EYEBROW))
    story.append(Paragraph("What Cortex Is and What It Does", H1))
    story.append(hr())

    story.append(Paragraph(
        "Cortex is a full-stack industrial knowledge management platform built for asset-intensive "
        "operations environments. The core problem it solves is straightforward to state but hard to fix: "
        "critical operational knowledge is scattered across PDF manuals, Excel inspection sheets, email "
        "threads, incident reports, and OEM documents, and the people who need that information spend a "
        "disproportionate share of their working hours hunting for it rather than using it.",
        BODY))

    story.append(Paragraph(
        "A 2024 McKinsey survey found that professionals in these industries spend roughly 35 percent of "
        "their time on information retrieval or recreation of documents that already exist. A NASSCOM-EY "
        "study of Indian manufacturing and energy plants found the average facility runs across 7 to 12 "
        "disconnected document systems. BIS Research linked this fragmentation to 18 to 22 percent of "
        "unplanned downtime events in Indian heavy industry, because maintenance teams make decisions "
        "without complete equipment history.",
        BODY))

    story.append(Paragraph(
        "Cortex addresses this by building a unified, queryable knowledge layer on top of whatever "
        "documents a plant already has. The system ingests PDFs, spreadsheets, DOCX files, email threads, "
        "and scanned images (with OCR), extracts structured entities from them, connects those entities "
        "into a knowledge graph, and then lets operators ask natural-language questions that draw from the "
        "full document corpus, not just a keyword match against a single file.",
        BODY))

    story.append(Paragraph("Key numbers from the current build:", H3))
    kn_data = [
        ["Metric", "Value"],
        ["Document types supported", "PDF, Excel/CSV, DOCX, .eml email, image (OCR)"],
        ["Chunk size", "512 tokens, 50-token overlap (sliding window)"],
        ["Embedding model", "all-MiniLM-L6-v2, 384 dimensions, fully local"],
        ["LLM tier (bulk)", "gpt-oss:20b-cloud via Ollama (no install required)"],
        ["LLM tier (reasoning)", "gpt-oss:120b-cloud via Ollama"],
        ["Knowledge graph node types", "7 (Equipment, Document, Incident, Regulation, Person, Location, Procedure)"],
        ["Allowed relationship types", "10 (MAINTAINED_BY, LOCATED_AT, HAS_INCIDENT, and others)"],
        ["Real-world test: OEM manual", "Grundfos CR/CRI/CRN manual, 73 pages, 129 chunks, parsed clean"],
        ["Real-world test: incident report", "CSB investigation PDF, 11 pages, auto-classified as incident_report"],
        ["Active modules", "5 (Ingestion, Copilot, RCA, Compliance, Lessons Learned)"],
        ["Infrastructure", "7 Docker services, single docker-compose.yml"],
    ]
    story.append(tbl(kn_data, col_widths=[6*cm, TW - 6*cm]))
    story.append(PageBreak())

    # =========================================================
    # 2. PROBLEM STATEMENT
    # =========================================================
    story.append(Paragraph("BACKGROUND", EYEBROW))
    story.append(Paragraph("The Knowledge Fragmentation Problem", H1))
    story.append(hr())

    story.append(Paragraph(
        "Industrial plants accumulate documentation over decades. A pump that has been in service for "
        "fifteen years has an OEM manual, years of maintenance work orders, inspection records, incident "
        "reports from any trips or failures, email threads where engineers discussed problems, and "
        "possibly scanned handwritten notes. None of these sources talk to each other. When a new "
        "technician needs to understand why that pump keeps vibrating, they have to locate each source "
        "individually, often across different systems, and mentally synthesize them.",
        BODY))

    story.append(Paragraph(
        "This is not a retrieval problem. Search engines can find documents. The actual gap is that no "
        "single system maintains the semantic relationships between entities across documents: that pump "
        "P-101 is a KSB Etanorm 080-065-200, that it lives in Unit 3, that it was repaired in May 2024 "
        "under work order WO-2024-0512, that the root cause was misalignment introduced in February 2024 "
        "(WO-2024-0188), and that the OEM manual specifies a 3-month lubrication interval which the plant "
        "was not following. That chain of facts crosses five different documents. A basic RAG chatbot "
        "retrieves semantically similar text, not entity-linked facts.",
        BODY))

    story.append(Paragraph("The knowledge cliff compounds this further.", H3))
    story.append(Paragraph(
        "Approximately 25 percent of India's experienced industrial engineers and operators are expected "
        "to retire within the next decade. The operational judgment they carry has never been written down "
        "in a structured way. When they leave, the knowledge goes with them. A platform that continuously "
        "captures and structures knowledge from routine operational documents can act as an institutional "
        "memory system that survives personnel changes.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 3. ARCHITECTURE OVERVIEW
    # =========================================================
    story.append(Paragraph("SYSTEM DESIGN", EYEBROW))
    story.append(Paragraph("Architecture Overview", H1))
    story.append(hr())

    story.append(Paragraph(
        "The system is organized into three horizontal layers: a frontend (Next.js), a backend API "
        "(FastAPI with async Python), and a storage/intelligence layer (PostgreSQL, Neo4j, Qdrant, MinIO). "
        "The LLM calls go through a local Ollama daemon, which proxies cloud-hosted models via Ollama's "
        "cloud inference API. This means no paid API keys are needed and no models need to be downloaded "
        "locally, but inference still happens at full model quality.",
        BODY))

    story.append(Paragraph("Service topology:", H3))
    svc_data = [
        ["Service", "Image / Tech", "Host Port", "Internal Port", "Role"],
        ["postgres",  "PostgreSQL 15",   "55432",     "5432",   "Document metadata, jobs, chat sessions"],
        ["neo4j",     "Neo4j 5",         "7474/7687", "7474/7687", "Knowledge graph (Bolt + HTTP)"],
        ["qdrant",    "Qdrant latest",   "6333/6334", "6333/6334", "Vector store for chunk embeddings"],
        ["minio",     "MinIO latest",    "9000/9001", "9000/9001", "Raw file object storage"],
        ["backend",   "Python 3.10 / FastAPI", "8000", "8000",  "API, parsers, agents, graph builder"],
        ["frontend",  "Node 20 / Next.js 14",  "3000", "3000",  "React UI, SSE client, graph viewer"],
    ]
    story.append(tbl(svc_data, col_widths=[2.2*cm, 3.5*cm, 2.2*cm, 2.2*cm, TW-10.1*cm]))

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("PostgreSQL runs on host port 55432 (not the default 5432) because the "
        "development machine has native PostgreSQL instances on ports 5432 and 5433. Within Docker, "
        "all services address the database at the standard internal port 5432.", BODY_SM))

    story.append(Paragraph("LLM connectivity:", H3))
    story.append(Paragraph(
        "The backend uses the official OpenAI Python SDK pointed at the Ollama daemon's base URL "
        "(http://localhost:11434/v1 on the host, http://host.docker.internal:11434/v1 from inside "
        "Docker). The API key is set to the literal string 'ollama'. Ollama transparently proxies "
        "requests for cloud-suffix model names (gpt-oss:20b-cloud, gpt-oss:120b-cloud) to Ollama's "
        "own inference servers. No model weights are stored locally.",
        BODY))

    story.append(Paragraph(
        "One practical detail: gpt-oss wraps JSON-mode responses in markdown code fences "
        "(```json ... ```) even when json_object mode is requested. The client.py module handles "
        "this with an extract_json() function that strips the fences before parsing. Without this, "
        "every entity extraction call fails with a json.JSONDecodeError.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 4. INGESTION PIPELINE
    # =========================================================
    story.append(Paragraph("MODULE 1", EYEBROW))
    story.append(Paragraph("Document Ingestion and Processing Pipeline", H1))
    story.append(hr())

    story.append(Paragraph(
        "Ingestion is a six-stage sequential pipeline. Each stage is independent and the graph "
        "build stage is explicitly best-effort: if Neo4j is unreachable or entity extraction fails, "
        "the document still gets indexed in Qdrant and the job finishes successfully. The failure "
        "is logged but does not block the user.",
        BODY))

    pipe_data = [
        ["Stage", "Code Location", "What Happens"],
        ["1. Parse", "backend/parsers/", "File bytes dispatched by extension to PDF, Excel, DOCX, email, or image parser. OCR runs on images via pytesseract. Returns text string + metadata."],
        ["2. Type Infer", "parsers/base.py", "If doc_type not explicit, infer from content keywords: 'work order', 'vibration', 'incident', 'OISD', etc. Returns one of 7 enum values."],
        ["3. Chunk", "utils/chunker.py", "Sliding window over text: 512-token target, 50-token overlap. Paragraph and sentence boundaries respected. _hard_split() handles oversized units."],
        ["4. Embed", "vector_store/qdrant.py", "all-MiniLM-L6-v2 via sentence-transformers. 384-dim vectors. Entirely local, zero network calls. Upserted to Qdrant with payload."],
        ["5. Entity Extract", "graph/entity_extraction.py", "gpt-oss:20b-cloud in JSON mode. Extracts equipment, persons, incidents, regulations, procedures, locations, relationships. SHA256 cache avoids re-extraction."],
        ["6. Graph Build", "graph/graph_builder.py", "MERGE-based upsert to Neo4j on natural keys (tag, name, code). Same entity tag across docs = same node. 10 allowed relationship types."],
    ]
    story.append(tbl(pipe_data, col_widths=[2.5*cm, 4*cm, TW - 6.5*cm]))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Chunker implementation detail:", H3))
    story.append(Paragraph(
        "The chunker tokenizes with tiktoken (cl100k_base). It tries to split at paragraph boundaries "
        "first, then sentence boundaries, then word boundaries. The _hard_split() function handles "
        "the edge case where a single paragraph exceeds the target token count (this happens with "
        "long tabular data in PDFs or densely packed procedure text). Earlier builds passed a hardcoded "
        "512 to _split_units regardless of what the caller specified, so the overlap logic was "
        "inconsistent. That was fixed by threading max_tokens through from chunk_text() to the "
        "internal helpers.",
        BODY))

    story.append(Paragraph("SHA256 extraction cache:", H3))
    story.append(Paragraph(
        "Entity extraction is the most expensive per-document operation because it calls the LLM once "
        "per chunk (or batches of chunks). To avoid re-extracting unchanged content during re-ingestion, "
        "the system hashes the chunk text and stores the result keyed by that hash. On re-ingest of the "
        "same file, cache hits skip the LLM call entirely. This matters most during testing when the same "
        "real-world documents are ingested repeatedly.",
        BODY))

    story.append(Paragraph("Supported formats:", H3))
    fmt_data = [
        ["Format", "Parser", "Key dependencies", "Notes"],
        [".pdf", "pdf_parser.py", "pypdf", "Text-layer PDFs. Multilingual PDFs (like the 73-page Grundfos manual) parse correctly because only the English section is relevant."],
        [".xlsx / .csv", "excel_parser.py", "openpyxl, pandas", "Rows converted to readable text. Column headers preserved. Numeric sensor readings retain units."],
        [".docx", "docx_parser.py", "python-docx", "Paragraph and table extraction. Heading styles used to infer structure."],
        [".eml", "email_parser.py", "email stdlib", "Thread-aware: extracts From, To, Date, Subject plus body of all parts. Multi-reply threads flattened into single text."],
        ["image (jpg/png/tiff)", "image_parser.py", "pytesseract, Pillow", "OCR via Tesseract. Preprocessing: grayscale + threshold. Used for scanned forms and handwritten notes."],
    ]
    story.append(tbl(fmt_data, col_widths=[2.2*cm, 3.2*cm, 3.2*cm, TW - 8.6*cm]))
    story.append(PageBreak())

    # =========================================================
    # 5. KNOWLEDGE GRAPH
    # =========================================================
    story.append(Paragraph("MODULE 2", EYEBROW))
    story.append(Paragraph("Knowledge Graph Layer", H1))
    story.append(hr())

    story.append(Paragraph(
        "The knowledge graph is the part of this system that separates it from a conventional RAG "
        "pipeline. Standard RAG retrieves text chunks by semantic similarity. If a user asks about "
        "pump P-101, it finds the chunks that mention P-101 and feeds them to the LLM. That works "
        "for answering questions about a single document. It does not work for questions like 'who "
        "else maintains the same equipment that had an incident in Unit 2' because those facts are "
        "spread across multiple documents and the relationship between them was never made explicit.",
        BODY))

    story.append(Paragraph(
        "The graph makes those relationships explicit. Equipment nodes are merged on their tag (P-101, "
        "C-150, V-200). Person nodes are merged on name. Regulation nodes are merged on code (OISD-STD-105). "
        "When a second document mentions P-101, the graph builder does a MERGE, not a CREATE, so there "
        "is still exactly one P-101 node, now with two Document neighbors instead of one. After ingesting "
        "all six sample documents, P-101 has neighbors from three different source files.",
        BODY))

    story.append(Paragraph("Node types and natural keys:", H3))
    node_data = [
        ["Node Label", "Natural Key (MERGE field)", "Other Properties"],
        ["Equipment",  "tag",          "name, description, manufacturer, location"],
        ["Document",   "id (UUID)",    "title, doc_type, filename, source, created_at"],
        ["Incident",   "id",           "description, date, severity, status"],
        ["Regulation", "code",         "name, body, category"],
        ["Person",     "name",         "role, department"],
        ["Location",   "name",         "unit, area"],
        ["Procedure",  "title",        "code, revision, category"],
    ]
    story.append(tbl(node_data, col_widths=[3*cm, 4.5*cm, TW - 7.5*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Allowed relationship types:", H3))
    rel_data = [
        ["Relationship",         "From",       "To",          "Meaning"],
        ["MAINTAINED_BY",        "Equipment",  "Person",       "Person performs maintenance on equipment"],
        ["LOCATED_AT",           "Equipment",  "Location",     "Equipment is physically in this location"],
        ["HAS_INCIDENT",         "Equipment",  "Incident",     "Equipment was involved in this incident"],
        ["REFERENCES_REGULATION","Document",   "Regulation",   "Document cites this regulatory standard"],
        ["DESCRIBES_PROCEDURE",  "Document",   "Procedure",    "Document describes this operating procedure"],
        ["CAUSED_BY",            "Incident",   "Equipment",    "Incident was caused by this equipment failure"],
        ["INVESTIGATED_BY",      "Incident",   "Person",       "Person investigated this incident"],
        ["AUTHORED",             "Person",     "Document",     "Person authored or co-authored this document"],
        ["REQUIRED_BY",          "Procedure",  "Regulation",   "Procedure is mandated by this regulation"],
        ["SIMILAR_TO",           "Incident",   "Incident",     "Incidents share failure pattern (from Lessons)"],
    ]
    story.append(tbl(rel_data, col_widths=[4*cm, 2.2*cm, 2.2*cm, TW - 8.4*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Relationship allowlisting prevents the LLM from creating arbitrary relationship types. "
        "gpt-oss occasionally returns relationship types like IS_PART_OF or USES_STANDARD that are "
        "not in the list. The graph builder silently drops these rather than creating spurious edges "
        "that would clutter the visualization.",
        BODY_SM))

    story.append(Paragraph("Graph queries used by agents:", H3))
    for q_text in [
        "get_asset_subgraph(tag): everything within 1-2 hops of an equipment tag. Used by the Copilot and RCA agents to inject graph context alongside the Qdrant chunks.",
        "get_all_nodes() / get_all_edges(): full graph dump for the visualization UI. Paginated at 300 nodes and 600 edges.",
        "search_entities(query): case-insensitive substring search across tag, name, code, description. Powers the graph search box.",
        "graph_stats(): node counts by label plus total relationship count. Displayed on the dashboard.",
    ]:
        story.append(bullet(q_text))

    story.append(PageBreak())

    # =========================================================
    # 6. EXPERT COPILOT
    # =========================================================
    story.append(Paragraph("MODULE 3", EYEBROW))
    story.append(Paragraph("Expert Knowledge Copilot", H1))
    story.append(hr())

    story.append(Paragraph(
        "The Copilot is the primary user-facing intelligence interface. It accepts natural-language "
        "questions and returns grounded answers with source citations, a confidence score, and detected "
        "asset tags. Responses stream token-by-token via Server-Sent Events so the user sees output "
        "appear progressively rather than waiting for the full response.",
        BODY))

    story.append(Paragraph("Hybrid retrieval:", H3))
    story.append(Paragraph(
        "The retriever runs two lookups in parallel. First, it embeds the query with all-MiniLM-L6-v2 "
        "and does a top-6 similarity search in Qdrant. Second, it scans the query text for asset tags "
        "using a regex pattern ([A-Z]{1,3}-\\d{2,4}) and queries Neo4j for the 1-2 hop subgraph around "
        "each detected tag. The graph context is serialized to a structured text block and prepended to "
        "the system prompt alongside the Qdrant chunks.",
        BODY))

    story.append(Paragraph(
        "This combination handles two different query types that pure semantic search handles poorly. "
        "For 'what does the OEM manual say about P-101 lubrication', Qdrant finds the relevant chunks "
        "by content similarity. For 'who else is connected to P-101 in the graph', the Neo4j query "
        "answers it directly from the relationship structure. Most real operational questions need both.",
        BODY))

    story.append(Paragraph("Confidence scoring:", H3))
    story.append(Paragraph(
        "Confidence is derived from the top Qdrant similarity score. Scores above 0.5 are HIGH, "
        "0.3 to 0.5 are MEDIUM, and below 0.3 are LOW. This is a proxy metric, not a calibrated "
        "probability. Its main purpose is to signal to the user whether the answer is drawing from "
        "closely matched content or from distant semantic matches.",
        BODY))

    story.append(Paragraph("Session persistence:", H3))
    story.append(Paragraph(
        "Each chat session has a UUID stored in PostgreSQL. The last N messages from the session "
        "are retrieved at the start of each turn and included in the context window so the LLM has "
        "conversation history. The session ID is stored on the client side and passed with each "
        "request. A complication in the FastAPI route is that SQLAlchemy's async session cannot be "
        "shared between the HTTP request scope and the streaming generator scope. The route uses a "
        "separate get_db_context() async context manager for the generator, keeping the two scopes "
        "independent.",
        BODY))

    story.append(Paragraph("Streaming and React StrictMode:", H3))
    story.append(Paragraph(
        "The SSE protocol sends three event types in sequence: a meta event with citations and "
        "confidence, many delta events with token text, and a done event. The frontend accumulates "
        "deltas into the message content field. React 18 StrictMode double-invokes state updaters in "
        "development mode, which caused every token to be appended twice (producing 'TheThe May May' "
        "style output). The fix is immutable updates: instead of mutating content, each updater "
        "returns a new object with content set to last.content + delta. Immutable updates are "
        "idempotent under double-invocation.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 7. MAINTENANCE RCA
    # =========================================================
    story.append(Paragraph("MODULE 4", EYEBROW))
    story.append(Paragraph("Maintenance RCA Agent", H1))
    story.append(hr())

    story.append(Paragraph(
        "The RCA module takes an equipment tag and produces a structured root cause analysis drawing "
        "from the full document corpus. The output is a typed Pydantic model with immediate_cause, "
        "contributing_factors, root_causes, evidence, recommendations, and a confidence field.",
        BODY))

    story.append(Paragraph(
        "For pump P-101, the expected RCA output (based on the six sample documents) is: immediate "
        "cause is outer-race spalling on the SKF 6310 drive-end bearing. Root cause 1 is shaft "
        "misalignment introduced during the February 2024 coupling replacement. Root cause 2 is "
        "lubrication interval at 6 months versus the OEM-specified 3 months. Evidence comes from "
        "three sources: the maintenance work order (vibration readings), the OEM manual (lubrication "
        "specification), and the inspection CSV (vibration trend showing two ALARM readings before "
        "repair). The agent synthesizes all three without any manual cross-referencing.",
        BODY))

    story.append(Paragraph(
        "For compressor C-150, the RCA identifies the cracked 2nd-stage discharge valve plate as "
        "immediate cause, valve plates at 9,200 hours against an 8,000-hour OEM replacement interval "
        "as root cause 1, and the absence of automated alarm-to-work-order escalation as root cause 2. "
        "The evidence chain specifically includes the rod-drop reading (0.48 mm on July 26, 2 days "
        "before the trip) which was logged but not escalated.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 8. COMPLIANCE
    # =========================================================
    story.append(Paragraph("MODULE 5", EYEBROW))
    story.append(Paragraph("Compliance Intelligence", H1))
    story.append(hr())

    story.append(Paragraph(
        "The compliance module scans all ingested documents against a fixed checklist of six "
        "requirements drawn from the Indian industrial regulatory frameworks relevant to the "
        "problem statement: OISD-STD-105, OISD-STD-106, PESO, Factory Act 1948, and OISD-STD-118.",
        BODY))

    checklist_data = [
        ["#", "Framework",       "Requirement Summary",                                             "Expected Status"],
        ["1", "OISD-STD-105",    "Preventive maintenance program for rotating equipment with defined intervals",   "PARTIAL"],
        ["2", "OISD-STD-106",    "Pressure vessel and relief valve inspection and certification records",           "PARTIAL"],
        ["3", "PESO",            "Hazardous area classification and licensing for flammable storage",               "MET"],
        ["4", "Factory Act 1948","Permit-to-work / lockout-tagout system for maintenance activities",              "MET"],
        ["5", "Factory Act 1948","Periodic safety inspections and worker PPE compliance records",                   "PARTIAL"],
        ["6", "OISD-STD-118",    "Incident reporting, investigation, and root-cause closure process",               "MET"],
    ]
    story.append(tbl(checklist_data, col_widths=[0.6*cm, 3*cm, TW - 7.4*cm, 2.2*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Items 1 and 2 are PARTIAL because the evidence shows the processes exist but had known gaps "
        "at the time of the most recent documents: P-101's lubrication interval was wrong (6 months "
        "instead of 3), and V-200's relief valve re-certification was pending as of the email thread. "
        "Item 5 is PARTIAL because PPE requirements appear in the SOP but no dedicated audit trail "
        "document was ingested.",
        BODY))

    story.append(Paragraph(
        "Each checklist item is evaluated independently by calling the LLM with all relevant document "
        "chunks as context. The LLM returns a JSON object with status, risk_level, evidence_found, "
        "gaps, and recommendations. The overall compliance score is a weighted average of the "
        "individual statuses.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 9. LESSONS LEARNED
    # =========================================================
    story.append(Paragraph("MODULE 6", EYEBROW))
    story.append(Paragraph("Lessons Learned Engine", H1))
    story.append(hr())

    story.append(Paragraph(
        "The Lessons Learned module serves two functions: pattern discovery across all ingested "
        "incidents, and similarity search to find incidents that resemble a described failure mode.",
        BODY))

    story.append(Paragraph(
        "Pattern discovery scans incident-type chunks and asks the LLM to identify recurring themes "
        "across the corpus. With the six sample documents, it finds three patterns: lubrication interval "
        "deviation causing bearing failure (P-101), overdue component replacement causing equipment "
        "trip (C-150 valve plates), and inspection finding not escalated to work order (C-150 rod drop). "
        "As more documents are ingested, the engine surfaces cross-site patterns that no individual "
        "document would reveal.",
        BODY))

    story.append(Paragraph(
        "Similarity search uses Qdrant directly: embed the query text, search against incident-type "
        "chunks, return the top matches with scores. A search for 'high temperature compressor trip' "
        "should return INC-2024-0731 (C-150, 154 degrees C trip) with a score above 0.75.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 10. FRONTEND
    # =========================================================
    story.append(Paragraph("FRONTEND", EYEBROW))
    story.append(Paragraph("Interface Design and Implementation", H1))
    story.append(hr())

    story.append(Paragraph(
        "The frontend is built with Next.js 14 (App Router), React 18, TypeScript, and Tailwind CSS. "
        "The design system is called Foundry: a warm near-black base color, a single amber/ember "
        "accent (#e8833a), engineering dot-grid backdrop, JetBrains Mono for data values and labels, "
        "Inter for body text, and solid panels with hairline borders. The design explicitly avoids "
        "the purple-to-cyan gradient look that is common in 2024-2026 AI product templates.",
        BODY))

    story.append(Paragraph("Pages and routes:", H3))
    page_data = [
        ["Route",          "Component",         "Function"],
        ["/",              "page.tsx",           "Dashboard: graph stats, recent documents, quick-start suggestions"],
        ["/upload",        "upload/page.tsx",    "Document upload with animated Pipeline component (Parse > Chunk > Embed > Graph stages)"],
        ["/chat",          "chat/page.tsx",      "Expert Copilot: SSE chat, confidence badge, citations, asset tag chips"],
        ["/graph",         "graph/page.tsx",     "Force-directed graph visualization of Neo4j entities and relationships"],
        ["/documents",     "documents/page.tsx", "Ingested document list with type badges and chunk counts"],
        ["/compliance",    "compliance/page.tsx","Compliance scan results with MET/PARTIAL/GAP color coding"],
        ["/rca/[tag]",     "rca/page.tsx",       "RCA result for a specific asset tag: immediate cause, root causes, evidence"],
        ["/lessons",       "lessons/page.tsx",   "Failure pattern list and similarity search interface"],
    ]
    story.append(tbl(page_data, col_widths=[2.5*cm, 3.5*cm, TW - 6*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Markdown rendering:", H3))
    story.append(Paragraph(
        "Copilot answers are rendered with react-markdown and remark-gfm. A clean() function runs "
        "before rendering to normalize citation tokens: the LLM sometimes outputs Jupyter-notebook-style "
        "citations like [1 dagger L7-L9] enclosed in Japanese corner brackets, which are stripped and "
        "replaced with clean [1] references.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 11. LLM LAYER
    # =========================================================
    story.append(Paragraph("LLM INTEGRATION", EYEBROW))
    story.append(Paragraph("Language Model Layer", H1))
    story.append(hr())

    story.append(Paragraph(
        "All LLM calls go through backend/llm/client.py. The module provides three public functions: "
        "complete() for non-streaming text, complete_json() for JSON-mode responses, and stream() "
        "for token-by-token streaming. The model tier (FAST or SMART) is a parameter on each call.",
        BODY))

    llm_data = [
        ["Function",        "Tier",  "Temperature", "Model",                 "Used for"],
        ["complete_json()", "FAST",  "0.1",         "gpt-oss:20b-cloud",     "Entity extraction, doc type inference, compliance evaluation, RCA structure"],
        ["stream()",        "SMART", "0.3",         "gpt-oss:120b-cloud",    "Copilot answers, RCA narrative, lessons pattern text"],
        ["complete()",      "FAST",  "0.2",         "gpt-oss:20b-cloud",     "Short factual lookups, confidence scoring"],
    ]
    story.append(tbl(llm_data, col_widths=[3*cm, 1.3*cm, 2*cm, 4*cm, TW - 10.3*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "The FAST/SMART split is a rate-limit and cost management strategy. Entity extraction runs "
        "once per document chunk during ingestion and is cached, so it can use the heavier SMART "
        "model. But compliance scans evaluate six checklist items per scan, and RCA pre-processing "
        "does multiple structured lookups, so those use the faster 20b model to stay within "
        "free-tier usage limits during a live demo.",
        BODY))

    story.append(Paragraph("JSON fence stripping:", H3))
    for line in [
        "gpt-oss:20b-cloud and gpt-oss:120b-cloud wrap JSON-mode responses in markdown code fences.",
        "The raw response looks like: ```json\\n{...}\\n``` rather than just the bare JSON object.",
        "extract_json() in client.py strips the opening ```json and closing ``` before calling json.loads().",
        "If stripping fails, a fallback span-detection routine finds the first { and last } and parses between them.",
        "Without this, 100% of entity extraction calls fail silently with a JSONDecodeError."
    ]:
        story.append(bullet(line))

    story.append(PageBreak())

    # =========================================================
    # 12. DATA MODEL
    # =========================================================
    story.append(Paragraph("DATA MODEL", EYEBROW))
    story.append(Paragraph("PostgreSQL Schema", H1))
    story.append(hr())

    story.append(Paragraph(
        "PostgreSQL holds three main tables: documents, ingestion_jobs, and chat_sessions (with a "
        "chat_messages child table). The database is accessed via SQLAlchemy with asyncpg as the "
        "async driver. All schemas are defined as SQLAlchemy ORM models in backend/db/models.py "
        "and created with Alembic migrations.",
        BODY))

    schema_data = [
        ["Table",             "Key Columns",                                             "Purpose"],
        ["documents",         "id (uuid pk), title, doc_type, filename, file_path, chunk_count, status, created_at", "One row per ingested file. Status tracks processing state."],
        ["ingestion_jobs",    "id (uuid pk), document_id (fk), status, error_message, started_at, finished_at", "One row per background ingestion job. Polled by the upload UI."],
        ["chat_sessions",     "id (uuid pk), created_at, updated_at",                   "Groups messages into a conversation thread."],
        ["chat_messages",     "id (uuid pk), session_id (fk), role, content, citations, confidence, created_at", "Individual messages. citations stored as JSONB."],
    ]
    story.append(tbl(schema_data, col_widths=[3*cm, 6*cm, TW - 9*cm]))

    story.append(PageBreak())

    # =========================================================
    # 13. REAL WORLD TESTING
    # =========================================================
    story.append(Paragraph("VALIDATION", EYEBROW))
    story.append(Paragraph("Real-World Document Testing", H1))
    story.append(hr())

    story.append(Paragraph(
        "The system was tested against two categories of documents: a curated set of six synthetic "
        "industrial documents (with cross-linked entities and known ground truth), and two real-world "
        "PDFs downloaded from public sources.",
        BODY))

    story.append(Paragraph("Synthetic test corpus (6 files):", H3))
    synth_data = [
        ["File",                                    "Type",               "Key Entities"],
        ["pump_P-101_maintenance_report.txt",       "maintenance_report", "P-101, SKF 6310, WO-2024-0512, R. Sharma, A. Mehta"],
        ["OEM_manual_P-101_excerpt.txt",            "oem_manual",         "P-101, KSB Etanorm 080-065-200, ISO 10816-3"],
        ["incident_report_C-150_compressor.txt",    "incident_report",    "C-150, INC-2024-0731, Ariel JGK/4, OISD-STD-118"],
        ["safety_procedure_hot_work.txt",           "safety_procedure",   "SOP-SAF-014, PESO, Factory Act 1948, P-101, V-200, C-150"],
        ["email_thread_V-200_relief_valve.eml",     "email",              "V-200, OISD-STD-106, S. Nair, A. Mehta"],
        ["inspection_records.csv",                  "inspection",         "P-101, V-200, C-150, E-301 (sensor readings over time)"],
    ]
    story.append(tbl(synth_data, col_widths=[5.5*cm, 3*cm, TW - 8.5*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Real-world PDFs tested:", H3))
    rw_data = [
        ["File",                             "Source",   "Size",   "Pages", "Chunks", "Classified as"],
        ["grundfos_CR_pump_manual.pdf",      "Grundfos", "9.8 MB", "73",    "129",    "oem_manual (auto)"],
        ["csb_investigation_report.pdf",     "U.S. CSB", "1.4 MB", "11",    "5",      "incident_report (auto)"],
    ]
    story.append(tbl(rw_data, col_widths=[5.5*cm, 2*cm, 1.8*cm, 1.5*cm, 2*cm, TW - 12.8*cm]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "The Grundfos manual is a deliberately hard test case. It is 73 pages, multilingual (29 "
        "language sections), and the valuable technical content is concentrated in the English "
        "section (pages 4-26). The parser handles it correctly because pypdf extracts text by "
        "character stream rather than by page layout, so the multilingual table of contents and "
        "distributor address appendix produce irrelevant chunks but do not corrupt the English "
        "technical content. The 129 chunks include the bearing replacement intervals, shaft seal "
        "specifications, fault-finding table, and operating limits, all of which are verifiable "
        "against the Q&A ground truth in QNA_GRUNDFOS_MANUAL.md.",
        BODY))

    story.append(Paragraph("Cross-document linking verification:", H3))
    story.append(Paragraph(
        "After ingesting all six synthetic documents, the Neo4j graph contains one P-101 Equipment "
        "node with Document neighbors from three different source files (maintenance report, OEM "
        "manual, and hot work SOP). This confirms that MERGE-on-tag is working: the same physical "
        "asset is represented by a single node regardless of how many documents mention it.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 14. DEPLOYMENT
    # =========================================================
    story.append(Paragraph("DEPLOYMENT", EYEBROW))
    story.append(Paragraph("Infrastructure and Startup", H1))
    story.append(hr())

    story.append(Paragraph(
        "The full stack runs in Docker Compose. A single docker-compose.yml defines all seven "
        "services with their environment variables, port mappings, volume mounts, and health checks. "
        "The backend's OLLAMA_BASE_URL is set to http://host.docker.internal:11434/v1 with an extra "
        "host entry (host-gateway) so it can reach the Ollama daemon running on the host machine. "
        "The frontend communicates with the backend via the NEXT_PUBLIC_API_URL environment variable.",
        BODY))

    story.append(Paragraph("Standard startup sequence:", H3))
    for step_text in [
        "Step 1: docker compose up -d (starts all 7 services; first run pulls images and builds containers, approximately 3-5 minutes)",
        "Step 2: docker compose logs -f backend (watch for 'Application startup complete' before using the UI)",
        "Step 3: Open http://localhost:3000 for the frontend, http://localhost:8000/docs for the FastAPI Swagger UI",
        "Step 4: Neo4j Browser at http://localhost:7474 (credentials: neo4j / change_me_neo4j)",
        "Step 5: MinIO console at http://localhost:9001 (credentials: minioadmin / change_me_minio)",
        "For development iteration on the frontend, run 'npm run dev' instead of npm start to avoid .next cache corruption when rebuilding while the server is running",
    ]:
        story.append(bullet(step_text))

    story.append(Paragraph("Environment variables (key values):", H3))
    env_data = [
        ["Variable",            "Value",                                      "Notes"],
        ["OLLAMA_API_KEY",       "ollama",                                    "Literal string; Ollama does not validate keys"],
        ["OLLAMA_BASE_URL",      "http://localhost:11434/v1",                 "Host-side; use host.docker.internal from Docker"],
        ["LLM_MODEL_FAST",       "gpt-oss:20b-cloud",                        "Bulk operations and structured JSON extraction"],
        ["LLM_MODEL_SMART",      "gpt-oss:120b-cloud",                       "Reasoning and streaming answers"],
        ["POSTGRES_URL",         "postgresql+asyncpg://...@localhost:55432/...", "Port 55432 to avoid host PostgreSQL conflict"],
        ["NEO4J_URI",            "bolt://localhost:7687",                     "Bolt protocol for graph queries"],
        ["QDRANT_URL",           "http://localhost:6333",                     "REST API for vector operations"],
    ]
    story.append(tbl(env_data, col_widths=[4*cm, 5.5*cm, TW - 9.5*cm]))

    story.append(PageBreak())

    # =========================================================
    # 15. KNOWN ISSUES / FIXES
    # =========================================================
    story.append(Paragraph("ENGINEERING LOG", EYEBROW))
    story.append(Paragraph("Issues Encountered and Resolutions", H1))
    story.append(hr())

    story.append(Paragraph(
        "This section documents the non-trivial technical problems encountered during development "
        "and how they were resolved. It is included because the solutions represent real engineering "
        "decisions rather than textbook implementations.",
        BODY))

    issue_data = [
        ["Issue",                              "Symptom",                                     "Root Cause",                          "Fix"],
        ["gpt-oss JSON fence wrapping",        "json.JSONDecodeError on every entity extraction", "Model wraps json_object output in ```json fences", "extract_json() strips fences before parsing; fallback span detection"],
        ["PostgreSQL port conflict",           "Connection refused on 5432",                  "Host has native PG v13 and v17 on 5432/5433", "Container mapped to host port 55432"],
        ["config.py .env path",                "Settings not loading in backend",             "Path resolved relative to CWD (backend/) not project root", "Path(__file__).resolve().parent.parent / '.env'"],
        ["Chunker oversized paragraphs",       "Chunks exceeding 512 tokens in output",       "_split_units used hardcoded 512 not caller's max_tokens", "Added _hard_split(); passed max_tokens through call chain"],
        [".txt no type inference",             "All .txt classified as 'general'",            "Early return for txt skipped infer_doc_type()",  "Moved type inference before the early return"],
        ["Blank graph labels",                 "Document and Incident nodes show empty labels", "UUID-keyed nodes had no tag/name/code", "display_key() added title and description fallbacks"],
        ["React StrictMode double tokens",     "Chat shows 'TheThe May May' doubled output",  "setMessages mutated last.content directly; StrictMode double-invokes updaters", "All 3 handlers use immutable spread: {...last, content: last.content + delta}"],
        ["Frontend .next corruption",          "MODULE_NOT_FOUND after rebuild",              "Rebuilt while next start was still running", "Always stop server, rm -rf .next, rebuild, restart"],
    ]
    story.append(tbl(issue_data, col_widths=[3*cm, 3.5*cm, 4*cm, TW - 10.5*cm]))

    story.append(PageBreak())

    # =========================================================
    # 16. EVALUATION
    # =========================================================
    story.append(Paragraph("EVALUATION", EYEBROW))
    story.append(Paragraph("Judging Criteria Alignment", H1))
    story.append(hr())

    story.append(Paragraph(
        "The problem statement specifies five judging criteria with defined weights. This section "
        "maps Cortex's implementation against each criterion.",
        BODY))

    eval_data = [
        ["Criterion",          "Weight", "How Cortex Addresses It"],
        ["Innovation",         "25%",    "Hybrid RAG + graph retrieval is not common in hackathon submissions. Most teams build pure RAG chatbots. The cross-document entity linking via Neo4j MERGE is a meaningfully different architecture that enables queries no text-only system can answer."],
        ["Business Impact",    "25%",    "Directly addresses the 35% time-on-search problem and the knowledge cliff. The compliance module maps to real Indian regulatory frameworks (OISD, PESO, Factory Act) with specific standard codes, not generic compliance language."],
        ["Technical Excellence","20%",   "6-stage pipeline, 7 node types, 10 relationship types, 5 parser formats, 2 LLM tiers, SHA256 extraction cache, immutable streaming state, SSE protocol, session persistence."],
        ["Scalability",        "15%",    "Stateless backend (jobs are async), vector DB scales horizontally, Neo4j handles enterprise graph sizes. The document processing pipeline is designed to run as background jobs without blocking the API."],
        ["User Experience",    "15%",    "Foundry design language (not a template). Animated pipeline stages on upload. Streaming answers with citations. Force-directed graph explorer. Compliance dashboard with color-coded gap analysis."],
    ]
    story.append(tbl(eval_data, col_widths=[3*cm, 1.5*cm, TW - 4.5*cm]))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "The system runs entirely on free infrastructure: Ollama cloud models require no paid API "
        "keys, all database software is open-source, and the Docker Compose setup runs on a standard "
        "developer laptop. This means the demo can run without any network dependencies beyond the "
        "Ollama cloud inference endpoint.",
        BODY))

    story.append(PageBreak())

    # =========================================================
    # 17. FILE STRUCTURE
    # =========================================================
    story.append(Paragraph("PROJECT STRUCTURE", EYEBROW))
    story.append(Paragraph("Repository Layout", H1))
    story.append(hr())

    tree = """
project root/
  backend/
    agents/          copilot.py  rca.py  compliance.py  lessons.py  retriever.py
    db/              models.py  database.py  migrations/
    graph/           neo4j_client.py  entity_extraction.py  graph_builder.py  queries.py
    llm/             client.py  (OpenAI SDK -> Ollama proxy)
    parsers/         pdf_parser.py  excel_parser.py  docx_parser.py  email_parser.py  image_parser.py
    routers/         chat.py  ingest.py  graph.py  documents.py  compliance.py  lessons.py
    services/        ingestion.py
    utils/           chunker.py
    vector_store/    qdrant.py
    config.py        (Pydantic-settings, .env from project root)
    main.py          (FastAPI app, CORS, router registration)
  frontend/
    src/app/         page.tsx  chat/  upload/  graph/  documents/  compliance/  rca/  lessons/
    src/components/  Markdown.tsx  Pipeline.tsx  Backdrop.tsx  ui/Badge.tsx
    src/lib/         api.ts  (streamChat, fetchGraph, runRCA, ...)
    tailwind.config.ts
    globals.css      (.panel, .eyebrow, .backdrop-grid, prose-chat)
  sample_data/       6 synthetic files + real_world/ subfolder
  eraser_diagrams/   5 .eraserdiagram files (paste at app.eraser.io)
  docker-compose.yml
  .env.example
  QNA_GROUND_TRUTH.md
  QNA_GRUNDFOS_MANUAL.md
  START.md
  DEMO_SCRIPT.md
  ARCHITECTURE.md
"""
    for line in tree.strip().split("\n"):
        story.append(Paragraph(line.replace(" ", "&nbsp;"), CODE))

    story.append(PageBreak())

    # =========================================================
    # 18. APPENDIX: ERASER DIAGRAMS
    # =========================================================
    story.append(Paragraph("APPENDIX", EYEBROW))
    story.append(Paragraph("Eraser.io Diagram Files", H1))
    story.append(hr())

    story.append(Paragraph(
        "Five architecture diagrams are provided as Eraser.io DSL files in the eraser_diagrams/ "
        "folder. To render them, open app.eraser.io, create a new diagram of the matching type, "
        "and paste the file contents into the code editor.",
        BODY))

    eraser_data = [
        ["File",                                 "Diagram Type",            "Contents"],
        ["01_system_architecture.eraserdiagram", "Cloud Architecture",      "Full service topology: Frontend, Backend, LLM, Storage layers with connections"],
        ["02_ingestion_pipeline.eraserdiagram",  "Flowchart",               "6-stage ingestion: Upload > Parse > TypeInfer > Chunk > Embed > Entity Extract > Graph Build"],
        ["03_knowledge_graph_schema.eraserdiagram","Entity Relationship",   "7 node types with properties and all 10 named relationship types"],
        ["04_agent_architecture.eraserdiagram",  "Flowchart",               "5 agents with routing, retrieval split (Qdrant + Neo4j), and LLM tier dispatch"],
        ["05_rag_retrieval_sequence.eraserdiagram","Sequence Diagram",      "Full SSE chat flow: User > Frontend > FastAPI > Retriever > Qdrant + Neo4j > LLM > SSE stream"],
    ]
    story.append(tbl(eraser_data, col_widths=[5*cm, 3*cm, TW - 8*cm]))

    story.append(Spacer(1, 1*cm))
    story.append(hr())
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Document generated: {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}. "
        "All technical specifications reflect the codebase state at the time of report generation.",
        META))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF generated: {out}")
    return out

if __name__ == "__main__":
    build()
