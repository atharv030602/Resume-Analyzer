from app.services import local_matcher


def test_matched_and_missing_split(resume, jd):
    result = local_matcher.analyze(resume, jd)
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.matched_skills
    # In the JD but not the resume.
    assert any("LangChain" == s or "LangGraph" == s for s in result.missing_skills)
    assert 0 <= result.fit_score <= 100


def test_empty_jd_is_neutral():
    result = local_matcher.analyze("Python developer", "")
    assert result.fit_score == 50


def test_suggestions_are_capped(resume, jd):
    result = local_matcher.analyze(resume, jd)
    assert 0 < len(result.suggestions) <= 6
