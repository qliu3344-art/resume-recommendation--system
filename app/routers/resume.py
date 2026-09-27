import os
import shutil

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.resume import Resume, ResumeFields
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeFieldsOut,
    ParseResponse,
)
from app.services.ai_extractor import extract_resume_fields
from app.services.dedup import check_duplicate
from app.services.desensitize import desensitize
from app.services.embedding import embed_text
from app.services.feature_text import build_dedup_text, build_retrieval_text
from app.services.normalize import (
    education_to_level,
    normalize_education,
    work_experience_months,
)
from app.services.parser import parse_file

router = APIRouter(prefix="/resumes", tags=["简历管理"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传简历文件（PDF/Word）。"""
    if not file.filename.lower().endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(400, "仅支持 PDF 和 Word 格式")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    resume = Resume(filename=file.filename, file_path=file_path, status="uploaded")
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=ResumeListResponse)
def list_resumes(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """简历列表。"""
    total = db.query(Resume).count()
    items = db.query(Resume).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """简历详情。"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")
    return resume


@router.post("/{resume_id}/parse", response_model=ParseResponse)
def parse_resume(resume_id: int, db: Session = Depends(get_db)):
    """解析简历：文件提取 + 两阶段AI解析 + 去重检查。"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")

    # 1. 文件解析（PDF 走分栏重排，Word 走文档结构）
    raw_text = parse_file(resume.file_path)
    resume.raw_text = raw_text

    # 2. 两阶段 AI 提取
    parsed = extract_resume_fields(raw_text)
    resume.parsed_data = parsed
    resume.status = "verified"

    # 3. 字段归一化。学历等级和年限在入库前算好并落成列，匹配时才能走
    #    B-tree 索引在数据库层过滤，而不是拉进 Python 逐条判断
    normalized_education = normalize_education(parsed.get("education"))
    education_level = education_to_level(normalized_education)
    work_months = work_experience_months(parsed.get("work_experience"))

    # 4. 去重：只用稳定锚点特征。重新解析时要排除自己的旧向量，
    #    否则会和自己比对出一个 1.0 的假重复
    dedup_text = build_dedup_text(parsed)
    is_dup, dup_id, score = check_duplicate(
        db, dedup_text, exclude_resume_id=resume_id
    )

    # 5. 写入结构化字段 + 两份特征向量
    existing = db.query(ResumeFields).filter(ResumeFields.resume_id == resume_id).first()
    if existing:
        db.delete(existing)
        db.flush()  # resume_id 上有唯一约束，旧行要先落库删掉

    retrieval_text = build_retrieval_text(parsed)
    fields = ResumeFields(
        resume_id=resume_id,
        name=parsed.get("name"),
        phone=parsed.get("phone"),
        id_card=parsed.get("id_card"),
        email=parsed.get("email"),
        education=normalized_education,
        school=parsed.get("school"),
        major=parsed.get("major"),
        graduation_year=parsed.get("graduation_year"),
        work_experience=parsed.get("work_experience"),
        project_experience=parsed.get("project_experience"),
        skills=parsed.get("skills"),
        education_level=education_level,
        work_months=work_months,
        dedup_vec=embed_text(dedup_text) if dedup_text else None,
        retrieval_vec=embed_text(retrieval_text) if retrieval_text else None,
        is_duplicate=is_dup,
    )
    db.add(fields)
    db.commit()
    db.refresh(fields)

    msg = "解析成功"
    if is_dup:
        msg = f"解析成功，但与简历 ID={dup_id} 疑似重复（相似度 {score:.2f}），待人工确认"

    return {"resume_id": resume_id, "status": resume.status, "fields": fields, "message": msg}


@router.get("/{resume_id}/desensitized", response_model=ResumeFieldsOut)
def get_desensitized(resume_id: int, db: Session = Depends(get_db)):
    """获取脱敏后的简历字段。

    只返回脱敏副本，不回写数据库——脱敏是读取时的一个视图，不是一次数据
    变更。回写会让原始值被覆盖掉，而且这个接口是 GET，不该有副作用。
    """
    fields = db.query(ResumeFields).filter(ResumeFields.resume_id == resume_id).first()
    if not fields:
        raise HTTPException(404, "简历字段不存在，请先解析")

    masked = desensitize({
        "phone": fields.phone,
        "id_card": fields.id_card,
        "email": fields.email,
    })
    return ResumeFieldsOut(
        id=fields.id,
        resume_id=fields.resume_id,
        name=fields.name,
        phone=masked.get("phone"),
        id_card=masked.get("id_card"),
        email=masked.get("email"),
        education=fields.education,
        school=fields.school,
        major=fields.major,
        graduation_year=fields.graduation_year,
        work_experience=fields.work_experience,
        project_experience=fields.project_experience,
        skills=fields.skills,
        education_level=fields.education_level,
        work_months=fields.work_months,
        is_duplicate=fields.is_duplicate,
    )
