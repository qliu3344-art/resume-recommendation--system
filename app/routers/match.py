from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job, JobMatch
from app.models.resume import ResumeFields
from app.schemas.job import MatchResponse, MatchResult
from app.services.matcher import match_job_to_resumes

router = APIRouter(prefix="/match", tags=["智能匹配"])


@router.post("/{job_id}", response_model=MatchResponse)
def match_resumes(job_id: int, top_k: int = 20, db: Session = Depends(get_db)):
    """为指定岗位匹配候选人（双层匹配）。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")

    # 执行匹配
    results = match_job_to_resumes(db, job, top_k=top_k)

    # 清除旧匹配记录
    db.query(JobMatch).filter(JobMatch.job_id == job_id).delete()

    # 保存匹配结果
    match_results = []
    for r in results:
        jm = JobMatch(
            job_id=job_id,
            resume_id=r["resume_id"],
            keyword_score=r["keyword_score"],
            semantic_score=r["semantic_score"],
            total_score=r["total_score"],
            match_details=r["match_details"],
        )
        db.add(jm)

        # 获取候选人姓名
        fields = db.query(ResumeFields).filter(ResumeFields.resume_id == r["resume_id"]).first()
        match_results.append(MatchResult(
            resume_id=r["resume_id"],
            name=fields.name if fields else None,
            keyword_score=r["keyword_score"],
            semantic_score=r["semantic_score"],
            total_score=r["total_score"],
            match_details=r["match_details"],
        ))

    db.commit()

    return MatchResponse(
        job_id=job_id,
        job_title=job.title,
        total_matches=len(match_results),
        results=match_results,
    )


@router.get("/{job_id}/results", response_model=MatchResponse)
def get_match_results(job_id: int, db: Session = Depends(get_db)):
    """查看岗位的历史匹配结果。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")

    matches = (
        db.query(JobMatch)
        .filter(JobMatch.job_id == job_id)
        .order_by(JobMatch.total_score.desc())
        .all()
    )

    results = []
    for m in matches:
        fields = db.query(ResumeFields).filter(ResumeFields.resume_id == m.resume_id).first()
        results.append(MatchResult(
            resume_id=m.resume_id,
            name=fields.name if fields else None,
            keyword_score=m.keyword_score,
            semantic_score=m.semantic_score,
            total_score=m.total_score,
            match_details=m.match_details,
        ))

    return MatchResponse(
        job_id=job_id,
        job_title=job.title,
        total_matches=len(results),
        results=results,
    )
