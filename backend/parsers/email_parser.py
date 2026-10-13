"""Email (.eml) parser → headers + body text.

Uses the stdlib email module (no extra deps) for .eml. .msg (Outlook) is
handled if `extract_msg` is installed, else raises a clear error.
"""
from __future__ import annotations

from email import policy
from email.parser import BytesParser

from parsers.base import ParsedDocument, infer_doc_type


def parse_email(data: bytes) -> ParsedDocument:
    # .msg files start with the OLE magic header.
    if data[:4] == b"\xd0\xcf\x11\xe0":
        return _parse_msg(data)
    return _parse_eml(data)


def _parse_eml(data: bytes) -> ParsedDocument:
    msg = BytesParser(policy=policy.default).parsebytes(data)
    headers = [
        f"From: {msg.get('from', '')}",
        f"To: {msg.get('to', '')}",
        f"Date: {msg.get('date', '')}",
        f"Subject: {msg.get('subject', '')}",
    ]

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_content()
    else:
        body = msg.get_content()

    full = "\n".join(headers) + "\n\n" + (body or "")
    return ParsedDocument(
        text=full.strip(),
        doc_type=infer_doc_type(full),
        page_count=1,
        metadata={"parser": "email.stdlib", "subject": msg.get("subject", "")},
    )


def _parse_msg(data: bytes) -> ParsedDocument:
    try:
        import tempfile

        import extract_msg
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            ".msg parsing needs `extract_msg` (pip install extract-msg)"
        ) from e

    with tempfile.NamedTemporaryFile(suffix=".msg", delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        m = extract_msg.Message(tmp.name)
        full = (
            f"From: {m.sender}\nTo: {m.to}\nDate: {m.date}\nSubject: {m.subject}\n\n{m.body}"
        )
    return ParsedDocument(
        text=full.strip(),
        doc_type=infer_doc_type(full),
        page_count=1,
        metadata={"parser": "extract_msg", "subject": m.subject},
    )
