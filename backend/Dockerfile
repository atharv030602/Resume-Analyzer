# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tooling for chromadb / onnxruntime wheels.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai.txt requirements-chroma.txt ./
# INSTALL_AI:     LangChain 1.x + providers (pure Python, light).
# INSTALL_CHROMA: persistent ChromaDB vectors (native deps, ~300 MB — skip on
#                 512 MB free tiers and use VECTOR_BACKEND=memory).
ARG INSTALL_AI=true
ARG INSTALL_CHROMA=false
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$INSTALL_AI" = "true" ]; then pip install -r requirements-ai.txt; fi \
    && if [ "$INSTALL_CHROMA" = "true" ]; then pip install -r requirements-chroma.txt; fi

COPY . .

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
