import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

for env_path in (
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
):
    if env_path.exists():
        load_dotenv(env_path, override=False)

INVOKE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
FALLBACK_MODEL = "meta/llama-3.1-8b-instruct"

DEFAULT_MODEL = os.getenv("NVIDIA_MODEL", FALLBACK_MODEL).strip() or FALLBACK_MODEL
ROUTING_MODEL = os.getenv("NVIDIA_MODEL", FALLBACK_MODEL).strip() or FALLBACK_MODEL

SLOW_CALL_THRESHOLD_S = 8.0

_client_instance: OpenAI | None = None


def _client() -> OpenAI:
    global _client_instance
    if _client_instance is None:
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
        logger.exception(
            "NVIDIA NIM chat call failed model=%s elapsed=%.2fs",
            use_model, time.time() - t0,
        )
        raise
    elapsed = time.time() - t0
    if elapsed > SLOW_CALL_THRESHOLD_S:
        logger.warning(
            "Slow NVIDIA NIM call model=%s elapsed=%.2fs msgs=%d",
            use_model, elapsed, len(messages),
        )
    return completion.choices[0].message.content or ""


def stream_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 512,
) -> "Iterator[str]":
    """Yield token chunks as they arrive from NVIDIA NIM."""
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
                    logger.info(
                        "First token model=%s ttft=%.2fs",
                        use_model, time.time() - t0,
                    )
                    first_token_logged = True
                yield delta
        elapsed = time.time() - t0
        if elapsed > SLOW_CALL_THRESHOLD_S:
            logger.warning(
                "Slow NVIDIA NIM stream model=%s elapsed=%.2fs msgs=%d",
                use_model, elapsed, len(messages),
            )
    except Exception:
        logger.exception(
            "NVIDIA NIM stream failed model=%s elapsed=%.2fs",
            use_model, time.time() - t0,
        )
        raise
