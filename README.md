# ResumeFit AI

Resume-to-job-description fit analyzer. Paste (or upload) a resume and a job description,
and get an instant fit score, matched/missing skills, and specific suggestions to close the gap —
plus a downloadable "optimized" resume highlighting the alignment.

**No AI API key required.** Matching is done locally with a curated skill-keyword engine
(200+ tech and soft skills, plus a fallback pass that picks up tools/brands not in the
dictionary) — instant, free, and works offline.

```
resumefit-ai/
├── backend/     FastAPI + SQLAlchemy + local keyword-matching engine
└── frontend/    Streamlit UI
```

## How it works

- **`POST /api/analyze`** — same matching engine, persists the result to MySQL.
- **`POST /api/analyze/agentic`** — the matching engine (used by the frontend):
  1. Scans the resume and job description against a curated skill dictionary
     ([`skills_data.py`](backend/app/services/skills_data.py))
  2. Picks up extra tools/brands the dictionary misses via a capitalized-token fallback pass
  3. Computes fit score = matched keywords ÷ total JD keywords
  4. Generates targeted suggestions for each missing skill
  5. Builds an "optimized resume" text (original + a keyword alignment summary)
- **`POST /api/analyze/upload`** — same engine, accepts a resume PDF (`multipart/form-data`,
  fields `resume_file` + `job_description`) instead of raw text. Text extraction via pypdf.

## Backend — run it

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # fill in DB_PASSWORD if you're using MySQL persistence
uvicorn app.main:app --reload --port 8000
```
Backend runs on `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

MySQL is optional — `/api/analyze/agentic` and `/api/analyze/upload` (what the frontend
uses) don't touch the database at all. Only `/api/analyze` persists results, and needs a
reachable MySQL instance (the app auto-creates the `resumefit` database on first run).

Quick test:
```bash
curl -X POST http://localhost:8000/api/analyze/agentic \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Java, Spring Boot, Hibernate, MySQL, REST APIs, basic Docker",
    "job_description": "Looking for a backend engineer with Spring Boot, Kubernetes, AWS, and CI/CD experience"
  }'
```

## Frontend — run it

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # points API_BASE_URL at your backend
streamlit run app.py
```
Opens on `http://localhost:8501`. Paste resume text or upload a PDF, paste the JD, run the
analysis, and get the fit gauge + matched/gap skill chips + suggestions + a downloadable
optimized resume.

## Project structure (backend)
```
app/
  main.py                    FastAPI app, CORS, table creation
  config.py                  Settings (pydantic-settings, reads .env)
  database.py                SQLAlchemy engine/session, auto-creates the DB
  models.py                  Analysis ORM model
  schemas.py                 Pydantic request/response models
  routers/analysis.py        /api/analyze, /api/analyze/agentic, /api/analyze/upload, /api/health
  services/
    local_matcher.py         The matching engine — score, matched/missing, suggestions, optimized resume
    skills_data.py            Curated skill dictionary + stopword lists
    pdf_service.py            PDF text extraction (pypdf)
    analysis_service.py       Single-shot analysis + DB persistence
    agents/orchestrator.py    Thin entry point the routers call into
```

## Deploying
- Backend: Render / Railway (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`), set DB env
  vars there if using persistence, point at a managed MySQL instance
- Frontend: Streamlit Community Cloud, or alongside the backend on Render
- Before deploying, tighten `allow_origins=["*"]` in `app/main.py` to your actual frontend origin

## Still to do
- [ ] Auth (skip for portfolio demo)
- [ ] Expand the skill dictionary / fallback heuristics for non-tech roles
- [ ] Rate limiting on the analyze endpoints
