"""Excel / CSV parser → flattened text with sheet + column context.

Tabular industrial data (inspection logs, maintenance schedules) is rendered
as readable "Sheet / Column: value" rows so the embedder and entity extractor
can pick up equipment tags and parameters from cells.
"""
from __future__ import annotations

import io

from parsers.base import ParsedDocument, infer_doc_type

_MAX_ROWS = 2000  # guard against giant sheets blowing up token counts


def parse_excel(filename: str, data: bytes) -> ParsedDocument:
    import pandas as pd

    is_csv = filename.lower().endswith(".csv")
    sheets: dict[str, "pd.DataFrame"] = {}

    if is_csv:
        sheets["Sheet1"] = pd.read_csv(io.BytesIO(data))
    else:
        xls = pd.ExcelFile(io.BytesIO(data))
        for name in xls.sheet_names:
            sheets[name] = xls.parse(name)

    parts: list[str] = []
    total_rows = 0
    for sheet_name, df in sheets.items():
        df = df.fillna("")
        cols = [str(c) for c in df.columns]
        parts.append(f"## Sheet: {sheet_name} (columns: {', '.join(cols)})")
        for _, row in df.head(_MAX_ROWS).iterrows():
            cells = [f"{col}: {row[col]}" for col in df.columns if str(row[col]).strip()]
            if cells:
                parts.append(" | ".join(cells))
            total_rows += 1

    full = "\n".join(parts)
    return ParsedDocument(
        text=full,
        doc_type=infer_doc_type(full, default="inspection_record"),
        page_count=len(sheets),
        metadata={"parser": "pandas", "sheets": list(sheets.keys()), "rows": total_rows},
    )
