import os
from typing import List, Dict

from openai import OpenAI


class CardiologyLLMAdapter:
    """Agent-specific LLM adapter for the cardiology workflow.

    Supports department-scoped API keys via environment variables like
    `CARDIOLOGY_OPENROUTER_API_KEY` or falls back to `OPENROUTER_API_KEY`.
    """

    def __init__(self, department: str = "cardiology") -> None:
        self.department = (department or "cardiology").strip().lower()
        self.provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free").strip()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2").strip()

        # Department-specific API key (e.g. CARDIOLOGY_OPENROUTER_API_KEY)
        dept_key_name = f"{self.department.upper()}_OPENROUTER_API_KEY"
        self.api_key = os.getenv(dept_key_name) or os.getenv("OPENROUTER_API_KEY", "").strip()

    def _client(self) -> OpenAI:
        if self.provider == "openrouter":
            key = self.api_key
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY not set (or department-specific key not provided)")
            return OpenAI(
                base_url=self.openrouter_base_url,
                api_key=key,
                default_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost"),
                    "X-Title": os.getenv("OPENROUTER_TITLE", "AllyAI"),
                },
            )

        if self.provider == "ollama":
            return OpenAI(base_url=f"{self.ollama_base_url}/v1", api_key="ollama")

        raise RuntimeError("Unsupported LLM provider configured")

    def chat(self, messages: List[Dict], model: str | None = None) -> str:
        selected_model = model or self.openrouter_model
        if self.provider == "ollama":
            selected_model = model or self.ollama_model

        try:
            response = self._client().chat.completions.create(
                model=selected_model,
                messages=messages,
                max_tokens=512,
                temperature=0.3,
                top_p=0.9,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"Cardiology LLM call failed: {exc}") from exc
