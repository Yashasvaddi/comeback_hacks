"""Document parser framework.

Each format parser turns raw bytes into a `ParsedDocument` (plain text +
metadata). Heavy dependencies (PaddleOCR, pandas) are imported lazily inside
the individual parsers so importing this module stays cheap and the API can
boot even if an optional parser's deps aren't installed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    text: str
    doc_type: str = "unknown"        # inferred category (see infer_doc_type)
    page_count: int = 0
    used_ocr: bool = False
    metadata: dict = field(default_factory=dict)


class UnsupportedFormat(Exception):
    pass


# Map file extensions to the parser module function name.
_EXT_DISPATCH = {
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".xls": "excel",
    ".csv": "excel",
    ".docx": "docx",
    ".eml": "email",
    ".msg": "email",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".txt": "text",
    ".md": "text",
}


def parse_document(filename: str, data: bytes) -> ParsedDocument:
    """Dispatch to the right parser by file extension."""
    ext = os.path.splitext(filename)[1].lower()
    kind = _EXT_DISPATCH.get(ext)
    if kind is None:
        raise UnsupportedFormat(f"No parser for extension {ext!r} ({filename})")

    if kind == "text":
        text = data.decode("utf-8", errors="replace")
        return ParsedDocument(
            text=text, doc_type=infer_doc_type(text), page_count=1,
            metadata={"parser": "plaintext"},
        )

    # Lazy import to avoid loading heavy deps unless needed.
    if kind == "pdf":
        from parsers.pdf_parser import parse_pdf

        return parse_pdf(data)
    if kind == "excel":
        from parsers.excel_parser import parse_excel

        return parse_excel(filename, data)
    if kind == "docx":
        from parsers.docx_parser import parse_docx

        return parse_docx(data)
    if kind == "email":
        from parsers.email_parser import parse_email

        return parse_email(data)
    if kind == "image":
        from parsers.image_parser import parse_image

        return parse_image(data)

    raise UnsupportedFormat(f"Unhandled parser kind {kind!r}")


# Keyword → doc_type heuristics. The Phase 3 entity step refines this with the LLM.
_TYPE_KEYWORDS = {
    "maintenance_report": ["maintenance", "work order", "serviced", "repair", "overhaul"],
    "incident_report": ["incident", "failure", "near miss", "accident", "root cause"],
    "safety_procedure": ["safety", "ppe", "hazard", "lockout", "permit to work"],
    "inspection_record": ["inspection", "checklist", "calibration", "test report"],
    "compliance_doc": ["oisd", "peso", "factory act", "regulation", "audit", "standard"],
    "sop": ["standard operating procedure", "sop", "startup", "shutdown procedure"],
}


def infer_doc_type(text: str, default: str = "unknown") -> str:
    """Cheap keyword classifier for an initial document category."""
    lowered = text[:4000].lower()
    best, best_hits = default, 0
    for doc_type, kws in _TYPE_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in lowered)
        if hits > best_hits:
            best, best_hits = doc_type, hits
    return best
