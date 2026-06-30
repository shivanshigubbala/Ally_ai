"""
chunker.py

Purpose:
--------
Split extracted text into smaller overlapping chunks.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input document text.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Characters shared between chunks.

    Returns:
        List of text chunks.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ],
    )

    return splitter.split_text(text)
from extract_pdf import extract_text
