from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:
    PdfReader = None


class DocError(RuntimeError):
    pass


def pdf_text(path: Path, max_chars: int = 8000) -> str:
    if PdfReader is None:
        raise DocError("PyPDF2 is not installed. Install with: pip install PyPDF2")
    if not path.exists():
        raise DocError(f"File not found: {path}")
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            parts.append(txt)
        if sum(len(p) for p in parts) >= max_chars:
            break
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def sniff_verification_tokens(text: str) -> list[str]:
    import re
    tokens = []
    # Common token patterns: hex, base64-ish, UUIDs
    patterns = [
        r"\b[0-9a-fA-F]{16,64}\b",
        r"\b[0-9A-Za-z_-]{16,128}\b",
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89ab][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b",
    ]
    for pat in patterns:
        tokens.extend(re.findall(pat, text))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        deduped.append(t)
    return deduped[:10]
