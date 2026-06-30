"""Word-based chunker (~400 words, ~80-word overlap, paragraph-aware).

Usage:
    python -m backend.ingest.chunker <pages.jsonl> <chunks.jsonl>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TARGET_WORDS = 400
OVERLAP_WORDS = 80


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras


def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        paras = _split_paragraphs(page["text"])
        words: list[str] = []
        para_ids: list[int] = []
        for pid, p in enumerate(paras):
            w = _words(p)
            words.extend(w)
            para_ids.extend([pid] * len(w))

        if not words:
            continue

        start = 0
        n = len(words)
        while start < n:
            end = min(start + TARGET_WORDS, n)
            chunk_words = words[start:end]

            chunk_text = " ".join(chunk_words)
            chunk_text = re.sub(r"\s+", " ", chunk_text).strip()
            if chunk_text:
                chunks.append({
                    "source": page["source"],
                    "page": page["page"],
                    "start_word": start,
                    "end_word": end,
                    "text": chunk_text,
                })
            if end == n:
                break
            start = max(end - OVERLAP_WORDS, start + 1)
    return chunks


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m backend.ingest.chunker <pages.jsonl> <chunks.jsonl>")
        return 2
    in_path, out_path = sys.argv[1], sys.argv[2]
    pages: list[dict] = []
    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(json.loads(line))
    chunks = chunk_pages(pages)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    avg = sum(len(c["text"]) for c in chunks) / max(len(chunks), 1)
    print(f"chunked into {len(chunks)} chunks (avg {avg:.0f} chars) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())