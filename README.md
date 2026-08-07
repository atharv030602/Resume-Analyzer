# ResumeFit AI

Resume-to-job-description fit analyzer. Paste (or upload) a resume and a job description,
and a chain of Claude-powered agents returns a calibrated fit score, matched/missing skills,
and specific suggestions to close the gap.

```
resumefit-ai/
├── src/            Spring Boot backend
├── frontend/        React (Vite) frontend
└── pom.xml
```

## How it works

Two analysis modes are exposed:

- **`POST /api/analyze`** — single Claude call, fast, returns fit score + skills + suggestions.
- **`POST /api/analyze/agentic`** — the full 4-agent chain (used by the frontend):
  1. **ResumeExtractorService** — parses the resume into a structured profile (skills, experience highlights, seniority)
  2. **JdAnalyzerService** — parses the JD into required vs. nice-to-have requirements
  3. **MatcherService** — semantically compares profile vs. requirements, computes the fit score and gap list
  4. **AdvisorService** — writes targeted, concrete suggestions based on the gap
- **`POST /api/analyze/upload`** — same agentic chain, but accepts a resume PDF (`multipart/form-data`, fields `resumeFile` + `jobDescription`) instead of raw text. Text extraction via Apache PDFBox.

## Backend — run it

1. **MySQL** running locally (the app auto-creates the `resumefit` database).
2. Env vars:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   export DB_USERNAME=root
   export DB_PASSWORD=your_mysql_password
   ```
3. ```bash
   mvn spring-boot:run
   ```
   Backend runs on `http://localhost:8080`.

Quick test:
```bash
curl -X POST http://localhost:8080/api/analyze/agentic \
  -H "Content-Type: application/json" \
  -d '{
    "resumeText": "Java, Spring Boot, Hibernate, MySQL, REST APIs, basic Docker",
    "jobDescription": "Looking for a backend engineer with Spring Boot, Kubernetes, AWS, and CI/CD experience"
  }'
```

## Frontend — run it

```bash
cd frontend
npm install
cp .env.example .env   # points VITE_API_BASE_URL at your backend
npm run dev
```
Opens on `http://localhost:5173`. Two input modes (paste text / upload PDF), then a results
panel with an instrument-style fit gauge, matched/gap skill chips, and suggestions.

## Project structure (backend)
```
controller/           AnalysisController — /api/analyze, /api/analyze/agentic, /api/analyze/upload, /api/health
service/               ClaudeApiService (raw Anthropic calls), AnalysisService (single-shot + persistence), PdfExtractionService
service/agent/         ResumeExtractorService, JdAnalyzerService, MatcherService, AdvisorService, AgentOrchestratorService
model/                 Analysis JPA entity
repository/            AnalysisRepository
dto/                   AnalyzeRequest/Response, ExtractedProfile, JdRequirements, MatchResult
```

## Deploying
- Backend: Render / Railway (set `ANTHROPIC_API_KEY`, `DB_USERNAME`, `DB_PASSWORD` as env vars there; point `spring.datasource.url` at a managed MySQL instance)
- Frontend: Vercel / Netlify (set `VITE_API_BASE_URL` to your deployed backend URL)
- Before deploying, tighten `@CrossOrigin(origins = "*")` in `AnalysisController` to your actual frontend origin.

## Still to do
- [ ] Auth (skip for portfolio demo, add if turning this into a real product)
- [ ] Rate limiting on the analyze endpoints (agentic mode = 4 API calls per request)
- [ ] Caching identical resume+JD pairs to cut Claude API cost
