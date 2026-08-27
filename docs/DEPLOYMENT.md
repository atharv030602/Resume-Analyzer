# ResumeFit AI 2.0 — Deployment guide

## Modes at a glance

| Mode | Command | Needs |
|---|---|---|
| Local, no AI, no DB | `uvicorn app.main:app --reload` with `DB_ENABLED=false` | Python 3.11+ |
| Local, full AI | `pip install -r requirements.txt -r requirements-ai.txt` + a provider key | Gemini or OpenAI key (add `-r requirements-chroma.txt` for persistent vectors) |
| Docker Compose | `docker compose up --build` | Docker, optional provider key in `.env` |
| Cloud | Backend on Render/Railway/Fly, frontend on Streamlit Cloud | managed MySQL (optional), Chroma volume |

---

## 1. Local — backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # core only — tests + deterministic mode
pip install -r requirements-ai.txt                     # optional — LangChain 1.x + providers (pure Python)
pip install -r requirements-chroma.txt                 # optional — persistent ChromaDB vectors (native wheels)
cp .env.example .env                                   # set LLM_PROVIDER + GOOGLE_API_KEY / OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/api/health` should report your `llm_provider`,
`ai_enabled`, and `vector_backend`.

### Getting a key
* **Gemini** — <https://aistudio.google.com/app/apikey> (free tier is enough for a demo). Set `LLM_PROVIDER=gemini`, `GOOGLE_API_KEY=…`.
* **OpenAI** — <https://platform.openai.com/api-keys> (paid). Set `LLM_PROVIDER=openai`, `OPENAI_API_KEY=…`.

## 2. Local — frontend

```bash
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "API_BASE_URL=http://localhost:8000/api" > .env
streamlit run app.py            # http://localhost:8501
```

## 3. Docker Compose (backend + frontend + MySQL + Chroma volume)

```bash
# optional: put GOOGLE_API_KEY / OPENAI_API_KEY / LLM_PROVIDER in a root .env
docker compose up --build
```
* Frontend: <http://localhost:8501>
* Backend: <http://localhost:8000/docs>
* Chroma persists in the `chroma_data` volume; MySQL in `mysql_data`.
* Backend image builds with `INSTALL_AI=true`; set `--build-arg INSTALL_AI=false` for a slim, AI-less image.

## 4. Cloud

### Backend — Render / Railway / Fly.io
* Build: `pip install -r requirements.txt -r requirements-ai.txt -r requirements-chroma.txt`
* Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* Env: `ENVIRONMENT=production`, `LOG_JSON=true`, `LLM_PROVIDER`, provider key,
  `CORS_ORIGINS=https://<your-streamlit-app>`, `VECTOR_BACKEND=chroma`,
  `CHROMA_DIR=/data/chroma` (attach a persistent disk at `/data`).
* MySQL: point `DB_*` at a managed instance, or set `DB_ENABLED=false`.
* Optional tracing: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`.

### Frontend — Streamlit Community Cloud
* App file: `frontend/app.py`
* Secret: `API_BASE_URL = "https://<your-backend>/api"`

### CI/CD — GitHub Actions
`.github/workflows/ci.yml` runs on every push/PR to `main`:
1. `ruff check` + `ruff format --check` on `app` and `tests`
2. `pytest` (deterministic, no keys, in-memory backends)
3. Docker build for backend (`INSTALL_AI=false`, cached) and frontend

To add continuous deploy, append a `deploy` job gated on `needs: [backend, docker]`
that calls your host's deploy hook (Render Deploy Hook URL / `flyctl deploy` /
`railway up`) using a repo secret.

## 5. Operational notes
* **Health/readiness probe:** `GET /api/health` (also wired as a Docker `HEALTHCHECK`).
* **Log correlation:** every log line carries `rid=<request-id>`; clients may send `x-request-id` and it is echoed back.
* **Scaling:** the API is stateless except for the in-memory fallbacks — with MySQL + Chroma configured you can run multiple replicas behind a load balancer.
* **Secrets:** never commit `.env`; it is git-ignored. Provider keys live only in host env / CI secrets.
