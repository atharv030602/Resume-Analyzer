from app.schemas import AnalyzeResponse
from app.services import local_matcher


def run(resume_text: str, job_description: str) -> AnalyzeResponse:
    """Local keyword-matching analysis — no external API calls."""
    return local_matcher.analyze(resume_text, job_description)
