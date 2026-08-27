"""Application settings.

All AI features are optional: if no provider API key is configured the app
still boots and every AI path falls back to the deterministic local engine.
Toggle behaviour with env vars (see .env.example).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App -------------------------------------------------------------
    app_name: str = "ResumeFit AI"
    app_version: str = "2.0.0"
    environment: str = "local"  # local | staging | production
    log_level: str = "INFO"
    log_json: bool = False  # True = structured JSON logs (prod)
    cors_origins: str = (
        "http://localhost:8501,https://resume-analyzer-nk4wmappwmh2hdz3prkoh4d.streamlit.app"
    )

    # --- Database (optional persistence) -------------------------------
    db_user: str = "root"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "resumefit"
    db_enabled: bool = True  # set False to skip MySQL entirely

    # --- LLM provider -------------------------------------------------
    llm_provider: str = "gemini"  # gemini | openai
    google_api_key: str = ""
    openai_api_key: str = ""
    # Point at an OpenAI-compatible gateway (e.g. OpenRouter:
    # https://openrouter.ai/api/v1). When set, that endpoint has no
    # /embeddings route, so embeddings fall back to the offline hasher.
    openai_base_url: str = ""
    gemini_chat_model: str = "gemini-1.5-flash"
    gemini_embed_model: str = "models/text-embedding-004"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 45

    # --- RAG / vector store ----------------------------------------------
    vector_backend: str = "chroma"  # chroma | memory
    chroma_dir: str = ".chroma"
    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4
    chat_history_turns: int = 8

    # --- Observability (LangSmith) ------------------------------------
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "resumefit-ai"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Derived ------------------------------------------------------
    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def active_api_key(self) -> str:
        """The API key for the currently selected provider (empty = AI disabled)."""
        return self.google_api_key if self.llm_provider.lower() == "gemini" else self.openai_api_key

    @property
    def ai_enabled(self) -> bool:
        return bool(self.active_api_key)


settings = Settings()
