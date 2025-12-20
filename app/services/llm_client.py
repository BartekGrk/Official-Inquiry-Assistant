"""LLM client for calling the configured provider."""
from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
import google.generativeai as genai
from openai import OpenAI, OpenAIError

from app.config import settings
from app.logging_config import logger


class LLMClient:
    """Wrapper around the configured chat completion API with retries."""

    def __init__(self) -> None:
        self.provider = settings.provider.lower()
        if self.provider not in {"openai", "google"}:
            raise ValueError("Unsupported provider configured")
        self._client: OpenAI | None = None
        self._google_model: Optional[genai.GenerativeModel] = None

    def _get_client(self) -> OpenAI:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY must be configured")
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def _get_google_model(self) -> genai.GenerativeModel:
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY must be configured")
        if self._google_model is None:
            genai.configure(api_key=settings.google_api_key)
            self._google_model = genai.GenerativeModel(settings.google_model)
        return self._google_model

    def complete_json(self, system_prompt: str, user_prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        """Call the chat completion endpoint enforcing JSON output."""

        backoff = 1.0
        for attempt in range(settings.max_retries):
            try:
                if self.provider == "openai":
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
                else:
                    model = self._get_google_model()
                    response = model.generate_content(
                        contents=[
                            {"role": "system", "parts": [system_prompt]},
                            {"role": "user", "parts": [user_prompt]},
                        ],
                        generation_config=genai.GenerationConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                        safety_settings=None,
                        request_options={"timeout": settings.request_timeout},
                    )
                    content = response.text or "{}"
                return json.loads(content)
            except (OpenAIError, httpx.HTTPError, json.JSONDecodeError) as exc:
                logger.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, settings.max_retries, exc)
                if attempt + 1 == settings.max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM call failed (attempt %s/%s): %s", attempt + 1, settings.max_retries, exc)
                if attempt + 1 == settings.max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError("LLM call failed after retries")


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient()
