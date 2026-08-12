# backend/services/claude_service.py

import os
import requests
from dataclasses import dataclass


@dataclass
class LlmResponse:
    success: bool
    content: str | None = None
    error: str | None = None


OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = os.environ.get("LLM_MODEL", "openrouter/free")


def ask_llm(user_question: str, data_context: dict | list | None = None) -> LlmResponse:
    if not OPENROUTER_API_KEY:
        return LlmResponse(success=False, error="OPENROUTER_API_KEY is not set")

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a data analysis assistant. Answer using only the provided dataset context.",
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
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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
    except requests.exceptions.RequestException as e:
        return LlmResponse(success=False, error=f"Could not reach OpenRouter API: {str(e)}")

    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return LlmResponse(success=False, error=f"Unexpected response shape: {data}")

    return LlmResponse(success=True, content=answer)
