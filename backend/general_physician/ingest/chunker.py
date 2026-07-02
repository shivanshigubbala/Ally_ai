"""Split extracted page text into smaller overlapping chunks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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


def chunk_pages(pages: list[dict], chunk_size: int = 1600,
                chunk_overlap: int = 320) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        text = str(page.get("text") or "").strip()
        if not text:
            continue
        for idx, chunk in enumerate(chunk_text(text, chunk_size, chunk_overlap), 1):
            chunks.append({
                "source": page.get("source", ""),
                "page": page.get("page"),
                "chunk": idx,
                "text": chunk,
            })
    return chunks


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m backend.general_physician.ingest.chunker <pages.jsonl> <chunks.jsonl>")
        return 2

    pages_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    pages: list[dict] = []
    with pages_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))

    chunks = chunk_pages(pages)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"wrote {len(chunks)} chunks to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
