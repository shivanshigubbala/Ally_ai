"""General Physician Knowledge Ingestion Pipeline.

Reads .txt files from knowledge/general_physician/, chunks them,
embeds with NVIDIA NIM (nv-embedqa-e5-v5), and stores in
the shared knowledge_chunks PostgreSQL table under
department='general physician'.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from backend.db.pgvector_tracker import (
    init_db,
    insert_knowledge_chunks,
    count_knowledge_chunks,
)
from backend.llm.embeddings import embed_passages

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BATCH_SIZE = 16
CHUNK_SIZE = 1600
CHUNK_OVERLAP = 320
MAX_CHARS_PER_CHUNK = 1200
DEPARTMENT = "general physician"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit - 200:
        cut = cut[:space]
    return cut + "..."


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:])
            break
        best_boundary = end
        for sep in ["\n\n", "\n", ". ", " "]:
            pos = text.rfind(sep, start + chunk_overlap, end)
            if pos != -1:
                best_boundary = pos + len(sep)
                break
        chunks.append(text[start:best_boundary])
        next_start = best_boundary - chunk_overlap
        if next_start <= start or next_start >= text_len:
            start = best_boundary
        else:
            start = next_start
    return [c.strip() for c in chunks if c.strip()]


def ingest_all_general_physician():
    knowledge_dir = Path(__file__).resolve().parents[3] / "knowledge" / "general_physician"
    if not knowledge_dir.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")

    txt_files = [f for f in sorted(knowledge_dir.glob("*.txt")) if f.name != ".gitkeep"]

    if not txt_files:
        logger.warning("No .txt files found in %s", knowledge_dir)
        return

    logger.info("Found %d text files in %s", len(txt_files), knowledge_dir)
    init_db()

    total_inserted = 0
    t_start = time.time()

    for txt_file in txt_files:
        logger.info("=" * 60)
        logger.info("Processing %s", txt_file.name)

        text = txt_file.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            logger.warning("  Empty file, skipping.")
            continue

        chunks = chunk_text(text)
        logger.info("  Generated %d chunks from %s", len(chunks), txt_file.name)

        if not chunks:
            continue

        inserted = 0
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_texts = [_truncate(c, MAX_CHARS_PER_CHUNK) for c in chunks[i:i + BATCH_SIZE]]
            try:
                embs = embed_passages(batch_texts)
            except Exception as exc:
                logger.error("  embedding batch %d failed: %s", i // BATCH_SIZE + 1, exc)
                continue

            insert_knowledge_chunks(
                department=DEPARTMENT,
                source=txt_file.stem,
                page=None,
                contents=batch_texts,
                embeddings=embs,
            )
            inserted += len(batch_texts)
            logger.info("  embedded %d/%d  (%.1fs)", inserted, len(chunks), time.time() - t_start)

        logger.info("  Successfully ingested %d chunks from %s", inserted, txt_file.name)
        total_inserted += inserted

    total_rows = count_knowledge_chunks(DEPARTMENT)
    logger.info("=" * 60)
    logger.info(
        "Done. Ingested %d total chunks. General physician table now has %d rows. Time: %.1fs",
        total_inserted,
        total_rows,
        time.time() - t_start,
    )


if __name__ == "__main__":
    ingest_all_general_physician()
