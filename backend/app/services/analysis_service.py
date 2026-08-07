from sqlalchemy.orm import Session

from app.models import Analysis
from app.schemas import AnalyzeResponse
from app.services import local_matcher


def single_shot(resume_text: str, job_description: str) -> AnalyzeResponse:
    return local_matcher.analyze(resume_text, job_description)


def persist(db: Session, resume_text: str, job_description: str, result: AnalyzeResponse) -> Analysis:
    entity = Analysis(
        resume_text=resume_text,
        job_description=job_description,
        fit_score=result.fit_score,
        matched_skills=", ".join(result.matched_skills),
        missing_skills=", ".join(result.missing_skills),
        suggestions=" | ".join(result.suggestions),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity
