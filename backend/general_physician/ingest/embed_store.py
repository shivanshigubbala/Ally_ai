"""Embed chunks and store them in pgvector.

Usage:
    python -m backend.general_physician.ingest.embed_store <chunks.jsonl> <department>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    from backend.db.pgvector_tracker import (  # noqa: E402
        count_knowledge_chunks,
        init_db,
        insert_knowledge_chunks,
    )
    from backend.llm.embeddings import embed_passages  # noqa: E402
except ImportError:
    from general_physician.db.pgvector_tracker import (  # noqa: E402
        count_knowledge_chunks,
        init_db,
        insert_knowledge_chunks,
    )
    from general_physician.llm.embeddings import embed_passages  # noqa: E402

BATCH_SIZE = 16
MAX_CHARS_PER_CHUNK = 1200  # ~250-300 tokens, well under 512-token limit


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # try to break on a word boundary
    space = cut.rfind(" ")
    if space > limit - 200:
        cut = cut[:space]
    return cut + "..."


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m backend.general_physician.ingest.embed_store <chunks.jsonl> <department>")
        return 2
    chunks_path, department = sys.argv[1], sys.argv[2]

    init_db()

    chunks: list[dict] = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    if not chunks:
        print("no chunks to embed")
        return 1

    inserted = 0
    skipped = 0
    t0 = time.time()
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [_truncate(c["text"], MAX_CHARS_PER_CHUNK) for c in batch]
        try:
            embs = embed_passages(texts)
        except Exception as exc:
            print(f"  embedding batch {i // BATCH_SIZE + 1} failed: {exc}")
            skipped += len(texts)
            continue
        page = batch[0].get("page")
        source = batch[0].get("source", "")
        insert_knowledge_chunks(
            department=department,
            source=source,
            page=page,
            contents=texts,
            embeddings=embs,
        )
        inserted += len(texts)
        if (i // BATCH_SIZE) % 5 == 0:
            print(f"  embedded {inserted}/{len(chunks)}  ({time.time() - t0:.1f}s)")

    total = count_knowledge_chunks(department)
    print(f"done. inserted {inserted} chunks for '{department}' "
          f"(skipped {skipped}). table now has {total} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
