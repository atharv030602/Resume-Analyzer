"""Resume-to-JD matching engine — pure keyword/skill matching, no external API calls.

Two layers of keyword detection:
1. A curated skill dictionary (skills_data.SKILLS) matched via word-boundary regex.
2. A fallback pass over the job description that picks up capitalized / acronym-like
   tokens not in the dictionary (catches tools/brands the curated list doesn't cover).
"""

import re
from collections import Counter

from app.schemas import AnalyzeResponse
from app.services.skills_data import GENERIC_STOPWORDS, JD_BOILERPLATE, SKILLS

_FALLBACK_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#/\-]{1,}")
_MAX_FALLBACK_TERMS = 15


def _build_pattern(term: str) -> re.Pattern:
    escaped = r"\s+".join(re.escape(word) for word in term.lower().split())
    return re.compile(r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])", re.IGNORECASE)


_COMPILED: dict[str, list[re.Pattern]] = {
    name: [_build_pattern(alias) for alias in aliases] for name, aliases in SKILLS.items()
}
_KNOWN_LOWER = {name.lower() for name in SKILLS} | {
    alias for aliases in SKILLS.values() for alias in aliases
}


def _scan_dict_skills(text: str) -> dict[str, str]:
    """canonical_lower -> display name, for every dictionary skill found in text."""
    hits = {}
    for name, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            hits[name.lower()] = name
    return hits


def _extract_fallback_terms(job_description: str) -> dict[str, str]:
    """canonical_lower -> original surface form, for capitalized/acronym tokens
    in the JD that aren't already covered by the skill dictionary."""
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}

    for tok in _FALLBACK_TOKEN_RE.findall(job_description):
        stripped = tok.strip(".-/#+")
        low = stripped.lower()
        if len(low) < 3 or low in GENERIC_STOPWORDS or low in JD_BOILERPLATE or low in _KNOWN_LOWER:
            continue
        looks_significant = (
            any(c.isupper() for c in tok[1:])  # e.g. GitHub, PostgreSQL
            or (tok.isupper() and len(tok) <= 6)  # e.g. SEO, ERP
        )
        if not looks_significant:
            continue
        counts[low] += 1
        display.setdefault(low, stripped)

    top = [term for term, _ in counts.most_common(_MAX_FALLBACK_TERMS)]
    return {term: display[term] for term in top}


def _present_in_resume(term_lower: str, resume_text: str, resume_dict_hits: dict[str, str]) -> bool:
    if term_lower in resume_dict_hits:
        return True
    return bool(_build_pattern(term_lower).search(resume_text))


def _build_suggestions(missing: list[str], matched: list[str], fit_score: int) -> list[str]:
    suggestions = [
        f"The job description mentions '{skill}' — if you have hands-on experience with it, "
        f"add it explicitly to your Skills or Experience section (exact keyword matches matter for ATS scans)."
        for skill in missing[:6]
    ]

    if not missing:
        suggestions.append(
            "Every keyword detected in this job description is already present in your resume — "
            "focus next on quantifying impact (numbers, metrics) in each bullet point."
        )
    elif fit_score < 40:
        suggestions.append(
            "Overall keyword overlap with this job description is low — consider whether this role "
            "is a strong fit, or substantially rework your Skills section around the JD's language."
        )
    elif fit_score < 70:
        suggestions.append(
            "You're a partial match — prioritize adding the missing skills above that you genuinely "
            "have experience with, worded exactly as the job description phrases them."
        )
    else:
        suggestions.append(
            "Strong keyword alignment — double check your matched skills are backed by specific, "
            "quantified examples in your experience bullets."
        )

    return suggestions[:6]


def _build_optimized_resume(resume_text: str, matched: list[str], missing: list[str]) -> str:
    lines = [resume_text.rstrip(), ""]
    lines.append("--- Keyword Alignment Summary (auto-generated, review before adding) ---")
    if matched:
        lines.append("Matched skills confirmed in this resume:")
        lines.append(", ".join(matched))
        lines.append("")
    if missing:
        lines.append("Skills the job description mentions that this resume doesn't — add ONLY if genuinely applicable:")
        lines.append(", ".join(missing))
    return "\n".join(lines)


def analyze(resume_text: str, job_description: str) -> AnalyzeResponse:
    jd_dict_hits = _scan_dict_skills(job_description)
    resume_dict_hits = _scan_dict_skills(resume_text)
    jd_fallback = _extract_fallback_terms(job_description)

    jd_keywords: dict[str, str] = {**jd_dict_hits, **jd_fallback}

    matched, missing = [], []
    for term_lower, display in jd_keywords.items():
        if _present_in_resume(term_lower, resume_text, resume_dict_hits):
            matched.append(display)
        else:
            missing.append(display)

    matched.sort()
    missing.sort()

    fit_score = round(len(matched) / len(jd_keywords) * 100) if jd_keywords else 50
    suggestions = _build_suggestions(missing, matched, fit_score)
    optimized_resume = _build_optimized_resume(resume_text, matched, missing)

    return AnalyzeResponse(
        fit_score=fit_score,
        matched_skills=matched,
        missing_skills=missing,
        suggestions=suggestions,
        optimized_resume=optimized_resume,
    )
