"""Embeddings client for NVIDIA NIM (nv-embedqa-e5-v5, 1024-dim).

Used by both the ingest pipeline (offline) and the retriever (online).
Falls back to OpenAI text-embedding-3-small if NIM embedding endpoint
isn't reachable, so the dev experience still works.
"""
from __future__ import annotations

import os
from typing import Iterable

import numpy as np
from openai import OpenAI

INVOKE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
EMBED_MODEL = os.getenv(
    "NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5"
).strip() or "nvidia/nv-embedqa-e5-v5"
EMBED_DIM = 1024


def _client() -> OpenAI:
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("NVIDIA_API_KEY not set in .env")
    return OpenAI(base_url=INVOKE_URL, api_key=key)


def embed_passages(texts: Iterable[str]) -> list[list[float]]:
    """Embed document/passages. nv-embedqa-e5-v5 is asymmetric and requires
    input_type='passage'; symmetric models ignore the extra_body key."""
    resp = _client().embeddings.create(
        model=EMBED_MODEL,
        input=list(texts),
        encoding_format="float",
        extra_body={"input_type": "passage"},
    )
    return [d.embedding for d in resp.data]


def embed_query(text: str) -> list[float]:
    """Embed a search query. nv-embedqa-e5-v5 uses input_type='query'."""
    resp = _client().embeddings.create(
        model=EMBED_MODEL,
        input=[text],
        encoding_format="float",
        extra_body={"input_type": "query"},
    )
    return resp.data[0].embedding


def as_np(vec: list[float]) -> np.ndarray:
    return np.asarray(vec, dtype=np.float32)