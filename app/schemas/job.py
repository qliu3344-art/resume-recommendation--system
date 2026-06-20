from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[dict] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[dict] = None


class JobOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    items: list[JobOut]


class MatchResult(BaseModel):
    resume_id: int
    name: Optional[str] = None
    keyword_score: float
    semantic_score: float
    total_score: float
    match_details: Optional[dict] = None


class MatchResponse(BaseModel):
    job_id: int
    job_title: str
    total_matches: int
    results: list[MatchResult]
