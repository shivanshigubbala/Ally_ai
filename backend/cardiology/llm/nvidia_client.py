"""Per-department LLM client shim — re-exports shared `backend.llm.nvidia_client`.

This file keeps the original import path (`backend.cardiology.llm.nvidia_client`) for
backwards compatibility, but delegates implementation to the shared client.
"""

from backend.llm.nvidia_client import chat, stream_chat, ROUTING_MODEL  # re-export

__all__ = ["chat", "stream_chat", "ROUTING_MODEL"]
