"""
extract_pdf.py

Purpose:
--------
Extract plain text from a PDF document.

Input:
    PDF file

Output:
    Plain text string

This module does NOT:
- Chunk text
- Generate embeddings
- Store data in the database
"""

import json
import sys
from pathlib import Path

try:
    import fitz  # type: ignore
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:
    PdfReader = None  # type: ignore


def extract_text(pdf_path: str | Path) -> str:
    """
    Extract text from every page of a PDF.

    Args:
        pdf_path (str | Path): Path to the PDF file.

    Returns:
        str: Complete extracted text.
    """

    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if _HAS_FITZ:
        doc = fitz.open(str(pdf_file))
        try:
            pages = []
            for page in doc:
                text = page.get_text("text") or ""
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        finally:
            doc.close()

    if PdfReader is None:
        raise ImportError(
            "No PDF reader available. Install pymupdf or pypdf: pip install pymupdf pypdf"
        )

    reader = PdfReader(str(pdf_file))
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            pages.append(text.strip())

    return "\n\n".join(pages)


def extract_pages(pdf_path: str | Path, patient_id: str | None = None) -> list[dict]:
    """Extract text page-by-page for downstream chunking."""
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if _HAS_FITZ:
        doc = fitz.open(str(pdf_file))
        try:
            pages = []
            for index, page in enumerate(doc, 1):
                text = (page.get_text("text") or "").strip()
                if text:
                    pages.append({
                        "source": pdf_file.name,
                        "page": index,
                        "text": text,
                        "patient_id": patient_id,
                    })
            return pages
        finally:
            doc.close()

    if PdfReader is None:
        raise ImportError(
            "No PDF reader available. Install pymupdf or pypdf: pip install pymupdf pypdf"
        )

    reader = PdfReader(str(pdf_file))
    pages = []
    for index, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append({
                "source": pdf_file.name,
                "page": index,
                "text": text,
                "patient_id": patient_id,
            })
    return pages


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m backend.neurology.ingest.extract_pdf <pdf> <pages.jsonl>")
        return 2

    pdf_path = sys.argv[1]
    output_path = Path(sys.argv[2])
    pages = extract_pages(pdf_path)
    with output_path.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")

    print(f"extracted {len(pages)} pages to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
