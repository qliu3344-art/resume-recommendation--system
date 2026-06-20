from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListResponse

router = APIRouter(prefix="/jobs", tags=["岗位管理"])


@router.post("", response_model=JobOut)
def create_job(data: JobCreate, db: Session = Depends(get_db)):
    """创建岗位。"""
    job = Job(title=data.title, description=data.description, requirements=data.requirements)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=JobListResponse)
def list_jobs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """岗位列表。"""
    total = db.query(Job).count()
    items = db.query(Job).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """岗位详情。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")
    return job


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, data: JobUpdate, db: Session = Depends(get_db)):
    """更新岗位。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """删除岗位。"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "岗位不存在")
    db.delete(job)
    db.commit()
    return {"message": "删除成功"}
