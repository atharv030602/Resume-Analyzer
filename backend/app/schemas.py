from __future__ import annotations

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# v1 — deterministic keyword analysis (unchanged, kept for back-compat)
# --------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)
    # v2 only: when set, the resume + JD are also indexed into this chat
    # session so the Resume Chat assistant can answer about them immediately.
    session_id: str | None = Field(default=None, min_length=6, max_length=64)


class AnalyzeResponse(BaseModel):
    fit_score: int
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    optimized_resume: str = ""


# --------------------------------------------------------------------------
# v2 — semantic analysis + ATS scoring
# --------------------------------------------------------------------------


class ATSCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ATSBreakdown(BaseModel):
    overall: int = Field(..., ge=0, le=100)
    keyword_coverage: int = Field(..., ge=0, le=100)
    semantic_similarity: int = Field(..., ge=0, le=100)
    formatting: int = Field(..., ge=0, le=100)
    impact_language: int = Field(..., ge=0, le=100)
    checks: list[ATSCheck] = Field(default_factory=list)


class SkillGap(BaseModel):
    skill: str
    importance: str = "medium"  # high | medium | low
    present_in_resume: bool = False
    recommendation: str = ""


class AnalyzeV2Response(BaseModel):
    fit_score: int
    semantic_score: int
    ats: ATSBreakdown
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    optimized_resume: str = ""
    ai_powered: bool = False
    degraded_reason: str | None = None
    agent_trace: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Chat assistant (RAG + conversation memory)
# --------------------------------------------------------------------------


class ChatIngestRequest(BaseModel):
    session_id: str = Field(..., min_length=6, max_length=64)
    resume_text: str = Field(..., min_length=1)
    job_description: str = Field(default="", min_length=0)


class ChatIngestResponse(BaseModel):
    session_id: str
    chunks_indexed: int


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=6, max_length=64)
    message: str = Field(..., min_length=1, max_length=4000)


class Citation(BaseModel):
    source: str
    snippet: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    history_turns: int = 0
    ai_powered: bool = False


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    ai_enabled: bool
    llm_provider: str
    vector_backend: str
    db_connected: bool
