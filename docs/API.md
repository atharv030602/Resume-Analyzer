# ResumeFit AI 2.0 — API reference

Base URL (local): `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs` · OpenAPI JSON: `/openapi.json`

Every response carries an `x-request-id` header. Handled errors use one envelope:

```json
{ "error": { "type": "bad_input", "message": "…", "request_id": "a1b2c3d4e5f6" } }
```

`type` ∈ `bad_input · document_parse_error · validation_error · llm_unavailable · upstream_error · http_error · internal_error`

---

## Health

### `GET /api/health` · `GET /api/v2/health`
```json
{
  "status": "ok", "version": "2.0.0", "environment": "local",
  "ai_enabled": false, "llm_provider": "gemini",
  "vector_backend": "memory", "db_connected": false
}
```

---

## v1 — deterministic keyword engine (unchanged, no API key needed)

| Method | Path | Body |
|---|---|---|
| POST | `/api/analyze` | `{resume_text, job_description}` — persists to MySQL |
| POST | `/api/analyze/agentic` | `{resume_text, job_description}` |
| POST | `/api/analyze/upload` | multipart: `resume_file` (PDF/DOCX), `job_description` |

Response: `{ fit_score, matched_skills[], missing_skills[], suggestions[], optimized_resume }`

---

## v2 — semantic + agentic + ATS

### `POST /api/v2/analyze`
Request:
```json
{ "resume_text": "…", "job_description": "…" }
```
Response `AnalyzeV2Response`:
```json
{
  "fit_score": 61,
  "semantic_score": 58,
  "ats": {
    "overall": 57, "keyword_coverage": 55, "semantic_similarity": 58,
    "formatting": 83, "impact_language": 40,
    "checks": [{ "name": "Contact email present", "passed": true, "detail": "Found." }]
  },
  "matched_skills": ["Python", "FastAPI", "Docker"],
  "missing_skills": ["LangChain", "LangGraph", "ChromaDB"],
  "skill_gaps": [
    { "skill": "LangChain", "importance": "high",
      "present_in_resume": false, "recommendation": "Add to Skills and show in a project bullet." }
  ],
  "suggestions": ["…"],
  "optimized_resume": "…",
  "ai_powered": false,
  "degraded_reason": "No LLM API key configured — using deterministic engine.",
  "agent_trace": ["mode=deterministic", "called skill_gap_tool", "called semantic_match_tool", "called ats_score_tool"]
}
```

### `POST /api/v2/analyze/upload`
multipart: `resume_file` (PDF/DOCX/TXT/MD, ≤5 MB), `job_description` (form field). Same response.

---

## v2 — chat assistant (RAG + memory)

### `POST /api/v2/chat/ingest`
```json
{ "session_id": "8charsmin", "resume_text": "…", "job_description": "…" }
```
→ `{ "session_id": "…", "chunks_indexed": 7 }` (resets any prior index for the session)

### `POST /api/v2/chat`
```json
{ "session_id": "…", "message": "Which required skills am I missing?" }
```
→
```json
{
  "session_id": "…",
  "answer": "…",
  "citations": [{ "source": "resume", "snippet": "…" }],
  "history_turns": 2,
  "ai_powered": true
}
```

### `GET /api/v2/chat/{session_id}/history`
→ `{ "session_id": "…", "messages": [{ "role": "user", "content": "…" }] }`

### `DELETE /api/v2/chat/{session_id}`
→ `{ "session_id": "…", "cleared": true }`

---

## curl quickstart

```bash
curl -s localhost:8000/api/v2/analyze -H 'content-type: application/json' -d '{
  "resume_text": "Python, FastAPI, Docker, REST APIs, PostgreSQL",
  "job_description": "GenAI Engineer: LangChain, LangGraph, RAG, ChromaDB, FastAPI, Docker, CI/CD"
}' | python -m json.tool

SID=$(python -c "import uuid;print(uuid.uuid4().hex)")
curl -s localhost:8000/api/v2/chat/ingest -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SID\",\"resume_text\":\"Python FastAPI Docker\",\"job_description\":\"LangChain RAG\"}"
curl -s localhost:8000/api/v2/chat -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SID\",\"message\":\"What am I missing?\"}"
```
