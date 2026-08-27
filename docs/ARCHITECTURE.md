# ResumeFit AI 2.0 — Architecture

## 1. System overview

```
                    ┌──────────────────────────┐
                    │   Streamlit frontend     │
                    │  Fit Analysis · Chat     │
                    └────────────┬─────────────┘
                                 │ REST / JSON
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI backend (app/)                     │
│                                                              │
│  routers/        health · analysis (v1+v2) · chat            │
│  middleware      request-id · timing · CORS · error envelope │
│                                                              │
│  services/                                                   │
│    document_service   PDF / DOCX / TXT extraction            │
│    local_matcher      deterministic keyword engine (v1)      │
│    embeddings_service semantic similarity (provider|hashing) │
│    ats_service        composite ATS score (4 signals)        │
│    suggestion_service LLM improvement tips (+ rule fallback) │
│    vectorstore        Chroma | in-memory, per-session        │
│    memory_service     conversation memory (MySQL | in-mem)   │
│    rag_service        retrieve → history → LLM → citations   │
│    agents/                                                   │
│      tools            skill_gap · semantic · ats · jd_kw     │
│      resume_agent     tool-calling agent | deterministic     │
│    analysis_v2_service  agent → ATS → suggestions → persist  │
│                                                              │
│  core/                                                       │
│    llm       provider factory (Gemini | OpenAI) + LangSmith  │
│    errors    typed AppError hierarchy + handlers             │
└───────┬─────────────────────┬───────────────────┬────────────┘
        │                     │                   │
        ▼                     ▼                   ▼
   ChromaDB (RAG)      MySQL (persistence)   Gemini / OpenAI
   .chroma/ volume     analysis, chat_*      chat + embeddings
```

## 2. Design principles

| Principle | How it shows up |
|---|---|
| **Graceful degradation** | No API key → deterministic engine + offline hashing embeddings. No MySQL → in-memory memory store. No ChromaDB → in-memory vector store. The service always boots and always answers. |
| **Provider-agnostic** | `LLM_PROVIDER=gemini\|openai` selects the model; `core/llm.py` is the only place that imports a provider SDK, lazily. |
| **Deterministic core, AI on top** | Scores (keyword, semantic, ATS) come from pure functions and are unit-tested without network. The LLM orchestrates and explains, it doesn't invent numbers. |
| **Observability** | Per-request `x-request-id` propagated through logs; optional LangSmith tracing on every LLM/agent call via env vars. |
| **Testability** | `requirements.txt` (core) has zero AI deps so CI runs the full suite fast; the AI stack lives in `requirements-ai.txt` (pure Python) + `requirements-chroma.txt` (native). |

## 3. Request flows

### `POST /api/v2/analyze`
1. `resume_agent.run()` — if `LLM_PROVIDER` key present, a LangChain 1.x
   `create_agent` (LangGraph tool-calling loop) decides which tools to call;
   otherwise a fixed pipeline runs the same tools.
2. Tools: `skill_gap_tool` (keyword match), `semantic_match_tool` (embedding
   cosine, stretched to 0–100), `ats_score_tool` (composite).
3. `suggestion_service.generate()` — LLM returns strict-JSON suggestions +
   ranked skill gaps; falls back to rule-based text on any failure.
4. `analysis_v2_service` blends `fit_score = 0.6·keyword + 0.4·semantic`,
   builds the optimised-resume text, persists to MySQL if available.

### `POST /api/v2/chat/ingest` → `POST /api/v2/chat`
1. Ingest: resume + JD are paragraph-packed into ~900-char chunks, embedded,
   written to a per-session Chroma collection (`session_<id>`).
2. Chat: top-k retrieval → last N turns from `memory_service` → system prompt
   constrains the model to the retrieved context → answer + citations.
3. Both user and assistant turns are appended to memory.

## 4. ATS score model

```
overall = 0.45·keyword_coverage      # JD keywords found verbatim
        + 0.30·semantic_similarity   # resume↔JD embedding cosine
        + 0.15·formatting            # email, phone, ≥3 sections, bullets, length, encoding
        + 0.10·impact_language       # quantified achievements + action verbs
```

Each sub-score is 0–100 and surfaced individually, with a pass/fail checklist
so the candidate knows *what* to fix, not just the number.

## 5. Data model

| Table | Purpose |
|---|---|
| `analysis` | one row per v1/v2 analysis: scores, matched/missing skills, suggestions, `ai_powered` |
| `chat_session` | one row per `session_id` |
| `chat_message` | ordered user/assistant turns, FK → `chat_session` |

Tables auto-create on startup (`Base.metadata.create_all`). Persistence is
optional — see `DB_ENABLED`.

## 6. Deployment topology

`docker-compose.yml` runs three services: `backend` (FastAPI + AI stack,
Chroma on a named volume), `frontend` (Streamlit), `mysql` (8.4 with a
healthcheck gate). See [DEPLOYMENT.md](DEPLOYMENT.md).
