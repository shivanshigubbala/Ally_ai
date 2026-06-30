"""Extract per-page text from a PDF using PyMuPDF.

Usage:
    python -m backend.ingest.extract_pdf <pdf_path> <out_jsonl>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import fitz  # type: ignore
except ImportError:
    print("pymupdf not installed. Run: pip install pymupdf")
    raise


def extract(pdf_path: str | Path) -> list[dict]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    doc = fitz.open(pdf_path)
    pages: list[dict] = []
    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        text = text.strip()
        if not text:
            continue
        pages.append({
            "page": i + 1,
            "source": pdf_path.name,
            "text": text,
        })
    doc.close()
    return pages


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m backend.ingest.extract_pdf <pdf> <out.jsonl>")
        return 2
    pdf_path, out_path = sys.argv[1], sys.argv[2]
    pages = extract(pdf_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    total_chars = sum(len(p["text"]) for p in pages)
    print(f"extracted {len(pages)} pages, {total_chars} chars -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())