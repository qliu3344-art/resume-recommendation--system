from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    matches = relationship("JobMatch", back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    keyword_score = Column(Float, default=0.0)
    semantic_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    match_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    job = relationship("Job", back_populates="matches")
    resume = relationship("Resume", back_populates="matches")
