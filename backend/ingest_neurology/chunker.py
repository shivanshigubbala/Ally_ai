"""
chunker.py

Purpose:
--------
Split extracted text into smaller overlapping token-based chunks.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping token chunks.

    Args:
        text: Input document text.
        chunk_size: Maximum tokens per chunk.
        chunk_overlap: Tokens shared between chunks.

    Returns:
        List of text chunks.
    """

    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            "",
        ],
    )

    return splitter.split_text(text)