"""Image OCR parser (PaddleOCR) for P&IDs, scanned drawings, photos.

PaddleOCR is heavy and loaded once, lazily, into a module-level singleton.
`ocr_image_bytes` is also reused by the PDF parser's scanned-page fallback.
"""
from __future__ import annotations

import io

from parsers.base import ParsedDocument, infer_doc_type

_ocr_engine = None


def _get_engine():
    """Lazily build the PaddleOCR engine (English, with angle classification)."""
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr_engine


def ocr_image_bytes(data: bytes) -> str:
    """Run OCR on raw image bytes, returning extracted text (lines joined)."""
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(image)

    engine = _get_engine()
    result = engine.ocr(arr, cls=True)
    if not result:
        return ""

    lines: list[str] = []
    for page in result:
        if not page:
            continue
        for line in page:
            # line = [box, (text, confidence)]
            try:
                text = line[1][0]
            except (IndexError, TypeError):
                continue
            if text:
                lines.append(text)
    return "\n".join(lines)


def parse_image(data: bytes) -> ParsedDocument:
    text = ocr_image_bytes(data)
    return ParsedDocument(
        text=text,
        doc_type=infer_doc_type(text),
        page_count=1,
        used_ocr=True,
        metadata={"parser": "paddleocr"},
    )
