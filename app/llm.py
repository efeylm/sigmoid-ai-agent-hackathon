# LLM factory
# Central place to build chat model clients from settings, so model, base URL
# and model-specific parameters are configured in one spot (.env).

from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.config import settings


def _common_kwargs(temperature: Optional[float] = None) -> Dict[str, Any]:
    """Optional parameters shared by LangChain and raw OpenAI clients.

    Newer GPT models are reasoning models: Chat Completions only allows tool calling
    with reasoning_effort="none", and some of them reject custom temperature values.
    Both are therefore driven from settings and only sent when configured.
    """
    kwargs: Dict[str, Any] = {}
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT
    temp = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
    if temp is not None and settings.OPENAI_SEND_TEMPERATURE:
        kwargs["temperature"] = temp
    return kwargs


def get_chat_llm(temperature: Optional[float] = None, **overrides: Any) -> ChatOpenAI:
    """Return a LangChain ChatOpenAI configured from settings."""
    params: Dict[str, Any] = {
        "api_key": settings.OPENAI_API_KEY,
        "base_url": settings.OPENAI_BASE_URL,
        "model": settings.OPENAI_MODEL_NAME,
        # Recent langchain-openai switches to the Responses API when tools are bound,
        # which returns content as a list of blocks. The code expects plain strings
        # from Chat Completions, so pin that API.
        "use_responses_api": False,
    }
    params.update(_common_kwargs(temperature))
    params.update(overrides)
    return ChatOpenAI(**params)


def get_openai_client() -> OpenAI:
    """Return a raw OpenAI client configured from settings."""
    return OpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY)


def completion_kwargs(max_completion_tokens: int, temperature: Optional[float] = None) -> Dict[str, Any]:
    """Extra kwargs for client.chat.completions.create()."""
    kwargs = _common_kwargs(temperature)
    kwargs["max_completion_tokens"] = max_completion_tokens
    return kwargs
