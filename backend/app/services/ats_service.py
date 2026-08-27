"""Composite ATS score.

Blends four signals a real applicant-tracking scan cares about:

    keyword_coverage   45%   JD keywords found verbatim in the resume
    semantic_similarity 30%  embedding cosine between resume and JD
    formatting          15%  parseability (contact info, sections, length)
    impact_language     10%  quantified achievements + strong action verbs
"""

from __future__ import annotations

import re

from app.schemas import ATSBreakdown, ATSCheck

_WEIGHTS = {
    "keyword_coverage": 0.45,
    "semantic_similarity": 0.30,
    "formatting": 0.15,
    "impact_language": 0.10,
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
_NUMBER_RE = re.compile(r"(\d+%|\$\d[\d,]*|\b\d[\d,]*\+?\b)")
_BULLET_RE = re.compile(r"^\s*([-*•‣▪]|\d+[.)])\s+", re.MULTILINE)
_SECTION_WORDS = ("experience", "education", "skills", "projects", "summary", "certification")
_ACTION_VERBS = {
    "built",
    "led",
    "designed",
    "developed",
    "implemented",
    "shipped",
    "launched",
    "improved",
    "reduced",
    "increased",
    "optimized",
    "automated",
    "migrated",
    "architected",
    "delivered",
    "owned",
    "scaled",
    "drove",
    "created",
    "deployed",
}


def _formatting_score(resume_text: str) -> tuple[int, list[ATSCheck]]:
    checks: list[ATSCheck] = []
    text = resume_text
    low = text.lower()
    words = len(text.split())

    has_email = bool(_EMAIL_RE.search(text))
    has_phone = bool(_PHONE_RE.search(text))
    sections = [w for w in _SECTION_WORDS if w in low]
    has_bullets = bool(_BULLET_RE.search(text))
    good_length = 250 <= words <= 1200
    # A high ratio of non-ASCII often means the PDF exported as glyph soup.
    non_ascii_ratio = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
    clean_encoding = non_ascii_ratio < 0.08

    checks.append(
        ATSCheck(
            name="Contact email present",
            passed=has_email,
            detail="Add a plain-text email near the top." if not has_email else "Found.",
        )
    )
    checks.append(
        ATSCheck(
            name="Phone number present",
            passed=has_phone,
            detail="Add a phone number." if not has_phone else "Found.",
        )
    )
    checks.append(
        ATSCheck(
            name="Standard sections",
            passed=len(sections) >= 3,
            detail=f"Detected: {', '.join(sections) or 'none'}. Use headings like Experience / Skills / Education.",
        )
    )
    checks.append(
        ATSCheck(
            name="Bulleted achievements",
            passed=has_bullets,
            detail="Use bullet points for experience items." if not has_bullets else "Found.",
        )
    )
    checks.append(
        ATSCheck(
            name="Reasonable length", passed=good_length, detail=f"{words} words. Aim for ~400-900."
        )
    )
    checks.append(
        ATSCheck(
            name="Clean text encoding",
            passed=clean_encoding,
            detail="Lots of unusual characters — export as a text-based PDF, not scanned."
            if not clean_encoding
            else "Parses cleanly.",
        )
    )

    passed = sum(c.passed for c in checks)
    return round(passed / len(checks) * 100), checks


def _impact_language_score(resume_text: str) -> tuple[int, list[ATSCheck]]:
    low = resume_text.lower()
    quantified = len(_NUMBER_RE.findall(resume_text))
    verbs_used = sorted({v for v in _ACTION_VERBS if re.search(rf"\b{v}\b", low)})

    quant_ok = quantified >= 3
    verbs_ok = len(verbs_used) >= 4
    score = round((min(quantified, 8) / 8) * 55 + (min(len(verbs_used), 8) / 8) * 45)

    checks = [
        ATSCheck(
            name="Quantified achievements",
            passed=quant_ok,
            detail=f"{quantified} metrics found. Add numbers (%, $, counts) to more bullets.",
        ),
        ATSCheck(
            name="Strong action verbs",
            passed=verbs_ok,
            detail=f"Used: {', '.join(verbs_used) or 'few'}. Start bullets with verbs like Built / Led / Reduced.",
        ),
    ]
    return max(0, min(100, score)), checks


def compute(
    resume_text: str,
    job_description: str,
    keyword_coverage: int,
    semantic_similarity: int,
) -> ATSBreakdown:
    fmt_score, fmt_checks = _formatting_score(resume_text)
    impact_score, impact_checks = _impact_language_score(resume_text)

    overall = round(
        keyword_coverage * _WEIGHTS["keyword_coverage"]
        + semantic_similarity * _WEIGHTS["semantic_similarity"]
        + fmt_score * _WEIGHTS["formatting"]
        + impact_score * _WEIGHTS["impact_language"]
    )

    return ATSBreakdown(
        overall=max(0, min(100, overall)),
        keyword_coverage=keyword_coverage,
        semantic_similarity=semantic_similarity,
        formatting=fmt_score,
        impact_language=impact_score,
        checks=fmt_checks + impact_checks,
    )
