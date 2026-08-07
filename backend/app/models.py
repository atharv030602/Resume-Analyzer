from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Analysis(Base):
    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_text: Mapped[str] = mapped_column(Text)
    job_description: Mapped[str] = mapped_column(Text)
    fit_score: Mapped[int] = mapped_column(Integer)
    matched_skills: Mapped[str] = mapped_column(Text)   # comma-separated
    missing_skills: Mapped[str] = mapped_column(Text)   # comma-separated
    suggestions: Mapped[str] = mapped_column(Text)      # " | "-separated
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
