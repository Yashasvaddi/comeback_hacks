"""PDF parser: native text extraction with an OCR fallback for scanned pages.

Strategy: extract text per page with pypdf. If a page yields little/no text
(scanned image), rasterize it and run OCR. OCR is lazy-loaded so plain digital
PDFs never pay the PaddleOCR import cost.
"""
from __future__ import annotations

import io

from parsers.base import ParsedDocument, infer_doc_type

# A page with fewer chars than this is treated as scanned → OCR.
_MIN_CHARS_PER_PAGE = 40


def parse_pdf(data: bytes) -> ParsedDocument:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    used_ocr = False

    for i, page in enumerate(reader.pages):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""

        if len(text) < _MIN_CHARS_PER_PAGE:
            ocr_text = _ocr_pdf_page(data, i)
            if len(ocr_text) > len(text):
                text = ocr_text
                used_ocr = True

        if text:
            pages.append(text)

    full = "\n\n".join(pages)
    return ParsedDocument(
        text=full,
        doc_type=infer_doc_type(full),
        page_count=len(reader.pages),
        used_ocr=used_ocr,
        metadata={"parser": "pypdf+ocr" if used_ocr else "pypdf"},
    )


def _ocr_pdf_page(data: bytes, page_index: int) -> str:
    """Rasterize one PDF page and OCR it. Returns '' if OCR unavailable."""
    try:
        from pdf2image import convert_from_bytes  # optional
        from parsers.image_parser import ocr_image_bytes

        images = convert_from_bytes(
            data, first_page=page_index + 1, last_page=page_index + 1, dpi=200
        )
        if not images:
            return ""
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return ocr_image_bytes(buf.getvalue())
    except Exception:
        # pdf2image/poppler or OCR not available — degrade gracefully.
        return ""
