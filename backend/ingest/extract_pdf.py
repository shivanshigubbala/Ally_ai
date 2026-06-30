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
