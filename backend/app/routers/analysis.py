from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services import analysis_service, pdf_service
from app.services.agents import orchestrator

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Single-shot analysis: one Claude call, structured JSON response."""
    try:
        result = analysis_service.single_shot(request.resume_text, request.job_description)
        analysis_service.persist(db, request.resume_text, request.job_description, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/analyze/agentic", response_model=AnalyzeResponse)
def analyze_agentic(request: AnalyzeRequest):
    """Agentic analysis: Extractor -> JD Analyzer -> Matcher -> Advisor (4 Claude calls)."""
    try:
        return orchestrator.run(request.resume_text, request.job_description)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/analyze/upload", response_model=AnalyzeResponse)
def analyze_upload(resume_file: UploadFile = File(...), job_description: str = Form(...)):
    """Same as /analyze/agentic but accepts a resume PDF upload instead of raw text."""
    try:
        resume_text = pdf_service.extract_text(resume_file)
        return orchestrator.run(resume_text, job_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/health")
def health():
    return {"status": "ResumeFit AI backend is running"}
