"""v2 analysis orchestration: agent -> ATS -> LLM suggestions -> persist."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.schemas import AnalyzeV2Response, ATSBreakdown
from app.services import local_matcher, suggestion_service
from app.services.agents import resume_agent

log = get_logger(__name__)


def analyze(resume_text: str, job_description: str) -> AnalyzeV2Response:
    agent_out = resume_agent.run(resume_text, job_description)

    matched = agent_out["matched_skills"]
    missing = agent_out["missing_skills"]
    keyword_coverage = agent_out["keyword_coverage"]
    semantic_score = agent_out["semantic_score"]
    ats = ATSBreakdown(**agent_out["ats"])

    suggestions, skill_gaps, ai_powered = suggestion_service.generate(
        resume_text, job_description, missing, matched, keyword_coverage
    )

    fit_score = round(0.6 * keyword_coverage + 0.4 * semantic_score)
    optimized_resume = local_matcher._build_optimized_resume(resume_text, matched, missing)

    degraded_reason = None
    if not settings.ai_enabled:
        degraded_reason = "No LLM API key configured — using deterministic engine."
    elif not ai_powered:
        degraded_reason = "LLM call failed — suggestions fell back to rule-based output."

    return AnalyzeV2Response(
        fit_score=fit_score,
        semantic_score=semantic_score,
        ats=ats,
        matched_skills=matched,
        missing_skills=missing,
        skill_gaps=skill_gaps,
        suggestions=suggestions,
        optimized_resume=optimized_resume,
        ai_powered=ai_powered,
        degraded_reason=degraded_reason,
        agent_trace=agent_out.get("trace", []),
    )


def persist(
    db: Session | None, resume_text: str, job_description: str, result: AnalyzeV2Response
) -> None:
    if db is None:
        return
    try:
        from app.models import Analysis

        db.add(
            Analysis(
                resume_text=resume_text,
                job_description=job_description,
                fit_score=result.fit_score,
                semantic_score=result.semantic_score,
                ats_score=result.ats.overall,
                matched_skills=", ".join(result.matched_skills),
                missing_skills=", ".join(result.missing_skills),
                suggestions=" | ".join(result.suggestions),
                ai_powered=result.ai_powered,
            )
        )
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        log.warning("Failed to persist analysis: %s", exc)
