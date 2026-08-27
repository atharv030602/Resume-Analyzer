"""LLM-backed resume improvement suggestions and skill-gap enrichment.

Falls back to deterministic, rule-based output whenever the LLM is not
configured or a call fails, so the endpoint always returns something useful.
"""

from __future__ import annotations

import json

from app.core.llm import ai_enabled, get_chat_model
from app.logging_config import get_logger
from app.schemas import SkillGap

log = get_logger(__name__)

_SYSTEM = (
    "You are an expert technical recruiter and ATS specialist. "
    "You give concise, specific, actionable resume feedback. "
    "Never invent experience the candidate does not have — frame gaps as "
    "'add if you have done this'."
)

_PROMPT = """Resume:
\"\"\"{resume}\"\"\"

Job description:
\"\"\"{jd}\"\"\"

Missing keywords detected: {missing}

Return STRICT JSON with this shape and nothing else:
{{
  "suggestions": ["<=6 short, imperative improvement tips"],
  "skill_gaps": [
    {{"skill": "...", "importance": "high|medium|low",
      "present_in_resume": false, "recommendation": "one sentence"}}
  ]
}}"""


def _rule_based(
    missing: list[str], matched: list[str], fit_score: int
) -> tuple[list[str], list[SkillGap]]:
    suggestions = [
        f"The JD calls for '{skill}'. If you've used it, name it explicitly in your "
        f"Skills section and back it with one bullet — exact keyword matches drive ATS scores."
        for skill in missing[:5]
    ]
    if not missing:
        suggestions.append(
            "Every JD keyword is already present — now quantify each bullet with metrics."
        )
    elif fit_score < 45:
        suggestions.append(
            "Keyword overlap is low; rework the Skills section around the JD's exact wording."
        )
    else:
        suggestions.append(
            "Partial match — prioritise the high-importance gaps you genuinely have experience with."
        )

    gaps = [
        SkillGap(
            skill=skill,
            importance="high" if i < 3 else "medium",
            present_in_resume=False,
            recommendation=f"Add '{skill}' to Skills and show it in a project or role bullet.",
        )
        for i, skill in enumerate(missing[:8])
    ]
    return suggestions[:6], gaps


def generate(
    resume_text: str,
    job_description: str,
    missing: list[str],
    matched: list[str],
    fit_score: int,
) -> tuple[list[str], list[SkillGap], bool]:
    """Returns (suggestions, skill_gaps, ai_powered)."""
    if not ai_enabled():
        s, g = _rule_based(missing, matched, fit_score)
        return s, g, False

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = get_chat_model()
        prompt = _PROMPT.format(
            resume=resume_text[:6000],
            jd=job_description[:6000],
            missing=", ".join(missing[:20]) or "none",
        )
        raw = model.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=prompt)]).content
        data = json.loads(_strip_fences(raw))

        suggestions = [str(x).strip() for x in data.get("suggestions", []) if str(x).strip()][:6]
        gaps = [
            SkillGap(
                skill=str(item.get("skill", "")).strip(),
                importance=str(item.get("importance", "medium")).lower(),
                present_in_resume=bool(item.get("present_in_resume", False)),
                recommendation=str(item.get("recommendation", "")).strip(),
            )
            for item in data.get("skill_gaps", [])
            if str(item.get("skill", "")).strip()
        ][:10]

        if not suggestions:
            raise ValueError("empty suggestions from model")
        return suggestions, gaps, True
    except Exception as exc:
        log.warning("LLM suggestion generation failed, using rule-based fallback: %s", exc)
        s, g = _rule_based(missing, matched, fit_score)
        return s, g, False


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()
