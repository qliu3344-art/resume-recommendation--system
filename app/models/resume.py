from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    status = Column(
        SAEnum("uploaded", "parsed", "verified", name="resume_status"),
        default="uploaded",
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    fields = relationship("ResumeFields", back_populates="resume", uselist=False)
    matches = relationship("JobMatch", back_populates="resume")


class ResumeFields(Base):
    __tablename__ = "resume_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    id_card = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    education = Column(String(50), nullable=True)
    school = Column(String(100), nullable=True)
    major = Column(String(100), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    work_experience = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)
    vector_id = Column(String(100), nullable=True)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    resume = relationship("Resume", back_populates="fields")
