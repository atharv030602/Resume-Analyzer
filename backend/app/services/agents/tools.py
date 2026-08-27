"""Callable tools the resume agent can invoke.

Each tool is a plain function (unit-testable, no LLM needed). ``build_langchain_tools``
wraps them as LangChain ``StructuredTool``s for the tool-calling agent.
"""

from __future__ import annotations

import json

from app.services import ats_service, embeddings_service, local_matcher


def jd_keyword_tool(job_description: str) -> str:
    """Extract the ranked skill/keyword list from a job description."""
    result = local_matcher.analyze("", job_description)
    keywords = result.missing_skills  # nothing matched against an empty resume
    return json.dumps({"keywords": keywords})


def skill_gap_tool(resume_text: str, job_description: str) -> str:
    """Return matched vs missing skills between a resume and a job description."""
    result = local_matcher.analyze(resume_text, job_description)
    return json.dumps(
        {
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "keyword_coverage": result.fit_score,
        }
    )


def semantic_match_tool(resume_text: str, job_description: str) -> str:
    """Return the 0-100 embedding-based semantic similarity score."""
    return json.dumps(
        {"semantic_score": embeddings_service.semantic_score(resume_text, job_description)}
    )


def ats_score_tool(resume_text: str, job_description: str) -> str:
    """Return the full ATS score breakdown for a resume against a job description."""
    match = local_matcher.analyze(resume_text, job_description)
    semantic = embeddings_service.semantic_score(resume_text, job_description)
    breakdown = ats_service.compute(resume_text, job_description, match.fit_score, semantic)
    return breakdown.model_dump_json()


TOOL_FUNCS = {
    "jd_keyword_tool": jd_keyword_tool,
    "skill_gap_tool": skill_gap_tool,
    "semantic_match_tool": semantic_match_tool,
    "ats_score_tool": ats_score_tool,
}


def build_langchain_tools(resume_text: str, job_description: str) -> list:
    """Bind the resume/JD into zero-arg LangChain tools for an AgentExecutor."""
    from langchain_core.tools import StructuredTool

    return [
        StructuredTool.from_function(
            func=lambda: skill_gap_tool(resume_text, job_description),
            name="skill_gap_tool",
            description="Matched vs missing skills between the resume and job description.",
        ),
        StructuredTool.from_function(
            func=lambda: semantic_match_tool(resume_text, job_description),
            name="semantic_match_tool",
            description="0-100 embedding-based semantic similarity of resume and job description.",
        ),
        StructuredTool.from_function(
            func=lambda: ats_score_tool(resume_text, job_description),
            name="ats_score_tool",
            description="Full ATS score breakdown (keyword, semantic, formatting, impact).",
        ),
        StructuredTool.from_function(
            func=lambda: jd_keyword_tool(job_description),
            name="jd_keyword_tool",
            description="Ranked skill/keyword list extracted from the job description.",
        ),
    ]
