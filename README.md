# ResumeFit AI 2.0

Production-grade resume analyzer: paste or upload a resume (PDF / DOCX) and a job
description, and get a **semantic fit score**, an **ATS score breakdown**,
**skill-gap analysis**, LLM **improvement suggestions**, and a **RAG chat
assistant with memory** over your resume + JD.

Built to demonstrate a full GenAI-engineering stack: **FastAPI microservice ·
LangChain · tool-calling agent · RAG · embeddings · ChromaDB vector store ·
conversation memory · Docker · GitHub Actions CI/CD · LangSmith observability**.

> **Runs with zero API keys.** Every AI path degrades gracefully to a
> deterministic engine + offline embeddings, so the service always boots and
> always answers. Add a **Gemini** or **OpenAI** key to switch on the LLM agent,
> LLM suggestions, provider embeddings, and grounded chat.

```
resumefit-ai/
├── backend/    FastAPI · LangChain · ChromaDB · SQLAlchemy · pytest
├── frontend/   Streamlit — Fit Analysis + Resume Chat tabs
├── docs/       ARCHITECTURE · API · DEPLOYMENT · RESUME_BULLETS
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Architecture

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full diagram and
request flows. In short:

- **`core/llm.py`** — the only module that imports a provider SDK (lazily);
  `LLM_PROVIDER=gemini|openai` picks the model.
- **`services/`** — deterministic `local_matcher` + `ats_service` + `embeddings_service`
  (pure, unit-tested, no network); `rag_service` + `vectorstore` (Chroma or
  in-memory); `memory_service` (MySQL or in-memory); `agents/` (tool-calling
  agent + deterministic fallback).
- **`analysis_v2_service`** — agent → ATS → LLM suggestions → persist.

## Endpoints

| | Path | Purpose |
|---|---|---|
| v1 | `POST /api/analyze`, `/api/analyze/agentic`, `/api/analyze/upload` | deterministic keyword engine (unchanged) |
| v2 | `POST /api/v2/analyze`, `/api/v2/analyze/upload` | semantic + agentic + ATS breakdown |
| v2 | `POST /api/v2/chat/ingest`, `POST /api/v2/chat` | RAG chat with memory + citations |
| v2 | `GET /api/v2/chat/{id}/history`, `DELETE /api/v2/chat/{id}` | conversation memory |
| — | `GET /api/health` | provider / vector-backend / DB status |

Full reference + curl examples: **[docs/API.md](docs/API.md)**.

## Run it — local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # core: tests + deterministic mode
pip install -r requirements-ai.txt                     # optional: LangChain 1.x + providers (pure Python, 3.11-3.14)
pip install -r requirements-chroma.txt                 # optional: ChromaDB persistence (needs wheels / Python <=3.13)
cp .env.example .env                                   # optional: set LLM_PROVIDER + a key
uvicorn app.main:app --reload --port 8000              # http://localhost:8000/docs
```

```bash
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "API_BASE_URL=http://localhost:8000/api" > .env
streamlit run app.py                                   # http://localhost:8501
```

Quick test (no key needed):
```bash
curl -s localhost:8000/api/v2/analyze -H 'content-type: application/json' -d '{
  "resume_text": "Python, FastAPI, Docker, REST APIs, PostgreSQL, CI/CD",
  "job_description": "GenAI Engineer: LangChain, LangGraph, RAG, ChromaDB, embeddings, FastAPI, Docker, CI/CD"
}' | python -m json.tool
```

## Run it — Docker

```bash
docker compose up --build     # backend :8000, frontend :8501, MySQL :3306, Chroma volume
```
Put `LLM_PROVIDER` / `GOOGLE_API_KEY` / `OPENAI_API_KEY` in a root `.env` to enable AI.

## Tests & CI

```bash
cd backend && pytest -q          # 22 tests, no network, no API keys
ruff check app tests && ruff format --check app tests
```
GitHub Actions (`.github/workflows/ci.yml`) runs lint + format + tests + Docker
builds on every push/PR to `main`.

## Enabling AI features

| Feature | Needs |
|---|---|
| LLM improvement suggestions + skill-gap enrichment | provider key |
| Tool-calling analysis agent | provider key + `requirements-ai.txt` |
| Grounded chat answers (vs. extractive) | provider key |
| Provider embeddings (vs. offline hashing) | provider key |
| ChromaDB persistence (vs. in-memory) | `requirements-chroma.txt`, `VECTOR_BACKEND=chroma` |
| MySQL persistence of analyses + chat | `DB_ENABLED=true` + reachable MySQL |
| LangSmith tracing | `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` |

Get a free Gemini key at <https://aistudio.google.com/app/apikey>
(`LLM_PROVIDER=gemini`), or an OpenAI key at
<https://platform.openai.com/api-keys> (`LLM_PROVIDER=openai`).

## Deploying

Render / Railway / Fly for the backend, Streamlit Community Cloud for the
frontend — step by step in **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## Recruiter / ATS pack

Resume bullets, keyword-coverage report, missing-skills analysis, ATS-score
estimate, and recruiter-feedback simulation: **[docs/RESUME_BULLETS.md](docs/RESUME_BULLETS.md)**.

## Roadmap — 3-project portfolio

1. **ResumeFit AI 2.0** (this repo) — RAG + tool-calling agent + FastAPI + CI/CD.
2. **Multi-Agent Career Assistant** — LangGraph, 5 agents, human-in-the-loop, eval framework.
3. **Enterprise Knowledge Assistant** — multi-doc RAG platform, website ingestion, citations, admin dashboard, AI governance.
