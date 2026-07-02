import logging
import os
import time
from typing import Iterator

from openai import OpenAI

logger = logging.getLogger(__name__)

INVOKE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
FALLBACK_MODEL = "meta/llama-3.1-8b-instruct"
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()

DEFAULT_MODEL = (
    os.getenv("OPENROUTER_MODEL", os.getenv("NVIDIA_MODEL", FALLBACK_MODEL)).strip()
    or FALLBACK_MODEL
)
ROUTING_MODEL = DEFAULT_MODEL

SLOW_CALL_THRESHOLD_S = 8.0

_client_instance: OpenAI | None = None


def _client() -> OpenAI:
    global _client_instance
    if _client_instance is None:
        provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        if not provider:
            provider = "openrouter" if os.getenv("OPENROUTER_API_KEY", "").strip() else "nvidia"

        if provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY not set in .env")
            default_headers = {
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost"),
                "X-Title": os.getenv("OPENROUTER_TITLE", "AllyAI"),
            }
            _client_instance = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=key,
                default_headers=default_headers,
            )
            return _client_instance

        if provider == "ollama":
            _client_instance = OpenAI(base_url=f"{OLLAMA_BASE_URL}/v1", api_key="ollama")
            return _client_instance

        key = os.getenv("NVIDIA_API_KEY", "").strip()
        if not key:
            raise RuntimeError("NVIDIA_API_KEY not set in .env")
        _client_instance = OpenAI(base_url=INVOKE_URL, api_key=key)
    return _client_instance


def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> str:
    use_model = model or DEFAULT_MODEL
    kwargs = dict(
        model=use_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stream=False,
    )

    t0 = time.time()
    try:
        completion = _client().chat.completions.create(**kwargs)
    except Exception:
        logger.exception("LLM chat call failed model=%s elapsed=%.2fs", use_model, time.time() - t0)
        raise

    elapsed = time.time() - t0
    if elapsed > SLOW_CALL_THRESHOLD_S:
        logger.warning("Slow LLM call model=%s elapsed=%.2fs msgs=%d", use_model, elapsed, len(messages))
    return completion.choices[0].message.content or ""


def stream_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> Iterator[str]:
    use_model = model or DEFAULT_MODEL
    t0 = time.time()
    try:
        response = _client().chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
        )
        first_token_logged = False
        for chunk in response:
            try:
                delta = chunk.choices[0].delta.content
            except (AttributeError, IndexError):
                delta = None
            if delta:
                if not first_token_logged:
                    logger.info("First token model=%s ttft=%.2fs", use_model, time.time() - t0)
                    first_token_logged = True
                yield delta

        elapsed = time.time() - t0
        if elapsed > SLOW_CALL_THRESHOLD_S:
            logger.warning("Slow LLM stream model=%s elapsed=%.2fs msgs=%d", use_model, elapsed, len(messages))
    except Exception:
        logger.exception("LLM stream failed model=%s elapsed=%.2fs", use_model, time.time() - t0)
        raise
