from app.services import ats_service


def test_composite_score_in_range(resume, jd):
    breakdown = ats_service.compute(resume, jd, keyword_coverage=55, semantic_similarity=60)
    assert 0 <= breakdown.overall <= 100
    for sub in (
        breakdown.keyword_coverage,
        breakdown.semantic_similarity,
        breakdown.formatting,
        breakdown.impact_language,
    ):
        assert 0 <= sub <= 100
    assert breakdown.checks


def test_good_resume_beats_bad_resume(jd):
    good = ats_service.compute(
        "john@x.com +91 90000 00000\nExperience\n- Built and led teams, reduced cost 30%, "
        "increased revenue 20%\nSkills\nPython\nEducation\nBE",
        jd,
        keyword_coverage=70,
        semantic_similarity=70,
    )
    bad = ats_service.compute(
        "just some plain text with no structure", jd, keyword_coverage=70, semantic_similarity=70
    )
    assert good.formatting > bad.formatting
    assert good.impact_language > bad.impact_language


def test_missing_contact_info_flagged():
    breakdown = ats_service.compute(
        "No contact here. Experience building things.", "python", 10, 10
    )
    email_check = next(c for c in breakdown.checks if c.name == "Contact email present")
    assert email_check.passed is False
