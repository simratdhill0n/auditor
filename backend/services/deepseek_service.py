# DeepSeek via OpenRouter - Person 1
"""Call DeepSeek (through OpenRouter) with optional dataset context."""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-chat"


@dataclass
class LlmResponse:
    success: bool
    content: str | None = None
    error: str | None = None


def _api_key() -> str | None:
    return os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY")


def _model() -> str:
    return os.environ.get("LLM_MODEL", DEFAULT_MODEL)


def ask_llm(user_question: str, data_context: dict | list | None = None) -> LlmResponse:
    """Send a question (plus optional Canada dataset context) to DeepSeek."""
    if not user_question or not str(user_question).strip():
        return LlmResponse(success=False, error="user_question is required")

    api_key = _api_key()
    if not api_key:
        return LlmResponse(
            success=False,
            error="DEEPSEEK_API_KEY is not set (OpenRouter key expected)",
        )

    payload = {
        "model": _model(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a data analysis assistant for Canadian open government data. "
                    "Answer using only the provided dataset context. "
                    "If the context is insufficient, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {user_question}\n\nData context: {data_context}",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return LlmResponse(success=False, error="OpenRouter API timed out")
    except requests.exceptions.RequestException as exc:
        return LlmResponse(success=False, error=f"Could not reach OpenRouter API: {exc}")
    except ValueError:
        return LlmResponse(success=False, error="OpenRouter API returned invalid JSON")

    try:
        answer = data["choices"][0]["message"]["content"]
    except (TypeError, KeyError, IndexError):
        return LlmResponse(success=False, error=f"Unexpected response shape: {data}")

    if not isinstance(answer, str) or not answer.strip():
        return LlmResponse(success=False, error="Model returned an empty response")

    return LlmResponse(success=True, content=answer)
