from functools import lru_cache
from typing import Any, Protocol

from fastapi import HTTPException, status
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI

from app.core.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
FREE_MODEL_ROUTER = "openrouter/free"


class AIProvider(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]: ...


class ChatProviderError(Exception):
    pass


class OpenRouterProvider:
    def __init__(self, api_key: str, model: str, timeout: int) -> None:
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=timeout,
            max_retries=0,
            default_headers={"X-OpenRouter-Title": "Daymark Todo"},
        )

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=700,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise ChatProviderError("The AI provider is temporarily unavailable.") from exc
        if not response.choices:
            raise ChatProviderError("The AI provider returned an empty response.")
        return response.choices[0].message.model_dump(exclude_none=True)


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    if settings.openrouter_api_key is None or not settings.openrouter_api_key.get_secret_value().strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI chat is not configured. Set OPENROUTER_API_KEY in the backend environment.",
        )
    return OpenRouterProvider(
        api_key=settings.openrouter_api_key.get_secret_value(),
        model=settings.ai_model,
        timeout=settings.ai_timeout_seconds,
    )
