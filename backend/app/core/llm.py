"""Provider-agnostic factory for chat models and embeddings.

Supported providers: ``gemini`` (langchain-google-genai) and ``openai``
(langchain-openai). Selection is driven by ``LLM_PROVIDER`` + the matching
API key. When no key is present:

* ``get_chat_model()`` raises ``LLMUnavailableError`` — callers fall back to
  the deterministic local engine.
* ``get_embeddings()`` returns a deterministic offline hashing vectoriser so
  semantic similarity / RAG still return meaningful (rougher) results.

LangChain packages are imported lazily so the service boots (and the test
suite runs) even when they are not installed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from app.config import settings
from app.core.errors import LLMUnavailableError
from app.logging_config import get_logger

log = get_logger(__name__)


def configure_langsmith() -> None:
    """Enable LangSmith tracing via env vars if configured."""
    if not (settings.langsmith_tracing and settings.langsmith_api_key):
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)
    log.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)


def ai_enabled() -> bool:
    return settings.ai_enabled


@lru_cache(maxsize=4)
def get_chat_model(temperature: float | None = None) -> Any:
    provider = settings.llm_provider.lower()
    temp = settings.llm_temperature if temperature is None else temperature

    if not settings.active_api_key:
        raise LLMUnavailableError(
            f"No API key configured for provider '{provider}'. "
            "Set GOOGLE_API_KEY or OPENAI_API_KEY to enable AI features."
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_chat_model,
            google_api_key=settings.google_api_key,
            temperature=temp,
            timeout=settings.llm_timeout_seconds,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            temperature=temp,
            timeout=settings.llm_timeout_seconds,
        )
    raise LLMUnavailableError(f"Unknown LLM_PROVIDER '{provider}' (expected gemini|openai).")


@lru_cache(maxsize=1)
def get_embeddings() -> Any:
    """Provider embeddings when a key is set, else the offline fallback."""
    provider = settings.llm_provider.lower()

    # OpenAI-compatible gateways (OpenRouter, etc.) don't serve embeddings.
    gateway = provider == "openai" and bool(settings.openai_base_url)

    if settings.active_api_key and not gateway:
        try:
            if provider == "gemini":
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                return GoogleGenerativeAIEmbeddings(
                    model=settings.gemini_embed_model,
                    google_api_key=settings.google_api_key,
                )
            if provider == "openai":
                from langchain_openai import OpenAIEmbeddings

                return OpenAIEmbeddings(
                    model=settings.openai_embed_model,
                    api_key=settings.openai_api_key,
                )
        except Exception as exc:  # pragma: no cover - dependency/network issue
            log.warning("Provider embeddings unavailable (%s); using offline fallback.", exc)
    elif gateway:
        log.info("OpenAI-compatible gateway in use; embeddings use the offline hasher.")

    from app.services.embeddings_service import HashingEmbeddings

    return HashingEmbeddings()


def reset_caches() -> None:
    """Used by tests that patch settings at runtime."""
    get_chat_model.cache_clear()
    get_embeddings.cache_clear()
