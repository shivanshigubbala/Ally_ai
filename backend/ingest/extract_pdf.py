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

from pypdf import PdfReader


def extract_text(pdf_path: str) -> str:
    """
    Extract text from every page of a PDF.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Complete extracted text.
    """

    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_file))

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text.strip())

    return "\n\n".join(pages)
