"""Compatibility shim for the neurology LLM client.

This keeps the historical import path available while delegating to the shared
NVIDIA client implementation.
"""

from __future__ import annotations

import os
from typing import Any

from backend.llm.nvidia_client import ROUTING_MODEL, chat, stream_chat


class NvidiaLLMClient:
    """Small compatibility wrapper with the methods expected by neurology services."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct").strip()

    def generate_response(
        self,
        *,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        history: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> str:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt or ""})
        return chat(messages, model=self.model)


llm_client = NvidiaLLMClient()

__all__ = ["NvidiaLLMClient", "llm_client", "chat", "stream_chat", "ROUTING_MODEL"]
