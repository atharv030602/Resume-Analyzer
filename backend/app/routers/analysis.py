from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import BadInputError
from app.database import get_db
from app.schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeV2Response
from app.services import analysis_service, analysis_v2_service, document_service
from app.services.agents import orchestrator

router = APIRouter(prefix="/api", tags=["analysis"])


# --------------------------------------------------------------------------
# v1 — deterministic keyword engine (unchanged behaviour)
# --------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    result = analysis_service.single_shot(request.resume_text, request.job_description)
    analysis_service.persist(db, request.resume_text, request.job_description, result)
    return result


@router.post("/analyze/agentic", response_model=AnalyzeResponse)
def analyze_agentic(request: AnalyzeRequest):
    return orchestrator.run(request.resume_text, request.job_description)


@router.post("/analyze/upload", response_model=AnalyzeResponse)
def analyze_upload(resume_file: UploadFile = File(...), job_description: str = Form(...)):
    resume_text = document_service.extract_text(resume_file.filename, resume_file.file.read())
    if not job_description.strip():
        raise BadInputError("job_description is required.")
    return orchestrator.run(resume_text, job_description)


# --------------------------------------------------------------------------
# v2 — semantic + agentic + ATS
# --------------------------------------------------------------------------


@router.post("/v2/analyze", response_model=AnalyzeV2Response)
def analyze_v2(request: AnalyzeRequest, db: Session = Depends(get_db)):
    result = analysis_v2_service.analyze(request.resume_text, request.job_description)
    analysis_v2_service.persist(db, request.resume_text, request.job_description, result)
    return result


@router.post("/v2/analyze/upload", response_model=AnalyzeV2Response)
def analyze_v2_upload(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
):
    resume_text = document_service.extract_text(resume_file.filename, resume_file.file.read())
    if not job_description.strip():
        raise BadInputError("job_description is required.")
    result = analysis_v2_service.analyze(resume_text, job_description)
    analysis_v2_service.persist(db, resume_text, job_description, result)
    return result
