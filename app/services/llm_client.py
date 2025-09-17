"""LLM client for calling the configured provider."""
from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Dict, List

import httpx
from openai import OpenAI, OpenAIError

from app.config import settings
from app.logging_config import logger


class LLMClient:
    """Wrapper around OpenAI chat completion API with retries."""

    def __init__(self) -> None:
        if settings.provider != "openai":
            raise ValueError("Only OpenAI provider is supported in MVP")
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY must be configured")
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        """Call the chat completion endpoint enforcing JSON output."""

        backoff = 1.0
        for attempt in range(settings.max_retries):
            try:
                response = self._get_client().chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    timeout=settings.request_timeout,
                )
                content = response.choices[0].message.content or "{}"
                return json.loads(content)
            except (OpenAIError, httpx.HTTPError, json.JSONDecodeError) as exc:
                logger.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, settings.max_retries, exc)
                if attempt + 1 == settings.max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError("LLM call failed after retries")


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient()
