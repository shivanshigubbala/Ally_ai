"""RAG retriever used by the doctor graph at runtime.

Builds a query from the patient's last few turns + the active symptom,
embeds it with NVIDIA NIM (nv-embedqa-e5-v5), and pulls the top-k
chunks from the department's knowledge base in pgvector.

If the embedding call or DB lookup fails, returns "" so the doctor
graph still works without RAG.
"""
from __future__ import annotations

import logging
from typing import Iterable

try:
    from backend.db.pgvector_tracker import search_knowledge
    from backend.llm.embeddings import embed_query
except ImportError:
    from db.pgvector_tracker import search_knowledge
    from llm.embeddings import embed_query

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
DEFAULT_MAX_CHARS = 3500


def retrieve(
    department: str,
    messages: Iterable[dict],
    top_k: int = DEFAULT_TOP_K,
    max_chars: int = DEFAULT_MAX_CHARS,
    chief_complaint: str | None = None,
) -> str:
    """Return a formatted context block for the LLM, or '' on failure."""
    msgs = list(messages)
    if not msgs:
        return ""

    query_parts = [m["content"] for m in msgs if m.get("role") == "user"][-3:]
    if chief_complaint:
        query_parts.insert(0, chief_complaint)
    if not query_parts:
        return ""
    query = " ".join(query_parts).strip()
    if not query:
        return ""

    try:
        vec = embed_query(query)
    except Exception as exc:
        logger.warning("embed_query failed: %s", exc)
        return ""

    try:
        hits = search_knowledge(department=department, embedding=vec, top_k=top_k)
    except Exception as exc:
        logger.warning("search_knowledge failed: %s", exc)
        return ""

    if not hits:
        return ""

    blocks: list[str] = []
    used = 0
    for i, h in enumerate(hits, 1):
        snippet = h["content"].strip()
        header = (
            f"[Excerpt {i} — {h.get('source', '?')} p.{h.get('page', '?')} "
            f"sim={h.get('similarity', 0):.2f}]"
        )
        block = f"{header}\n{snippet}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 200:
                block = block[:remaining] + "..."
                blocks.append(block)
            break
        blocks.append(block)
        used += len(block)

    return "\n\n".join(blocks)