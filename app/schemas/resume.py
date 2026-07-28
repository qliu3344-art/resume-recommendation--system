from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ResumeFieldsOut(BaseModel):
    id: int
    resume_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    id_card: Optional[str] = None
    email: Optional[str] = None
    education: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    work_experience: Optional[list] = None
    project_experience: Optional[list] = None
    skills: Optional[list] = None
    is_duplicate: bool = False

    class Config:
        from_attributes = True


class ResumeDetailResponse(BaseModel):
    id: int
    filename: str
    status: str
    raw_text: Optional[str] = None
    parsed_data: Optional[dict] = None
    fields: Optional[ResumeFieldsOut] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResumeListResponse(BaseModel):
    total: int
    items: list[ResumeUploadResponse]


class ParseResponse(BaseModel):
    resume_id: int
    status: str
    fields: Optional[ResumeFieldsOut] = None
    message: str
