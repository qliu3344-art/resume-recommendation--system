import os
import shutil

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resume import Resume, ResumeFields
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeDetailResponse,
    ResumeListResponse,
    ResumeFieldsOut,
    ParseResponse,
)
from app.services.parser import parse_file
from app.services.ai_extractor import extract_resume_fields
from app.services.dedup import get_dedup
from app.services.desensitize import desensitize
from app.services.normalize import normalize_education
from app.config import settings

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

    # 1. 文件解析
    raw_text = parse_file(resume.file_path)
    resume.raw_text = raw_text

    # 2. 两阶段 AI 提取
    parsed = extract_resume_fields(raw_text)
    resume.parsed_data = parsed
    resume.status = "verified"

    # 3. 去重检查
    dedup_text = f"{parsed.get('name', '')} {parsed.get('school', '')} {' '.join(w.get('company', '') for w in parsed.get('work_experience', []))}"
    dedup = get_dedup()
    is_dup, dup_id, score = dedup.check_duplicate(dedup_text)

    # 4. 存入结构化字段表
    existing = db.query(ResumeFields).filter(ResumeFields.resume_id == resume_id).first()
    if existing:
        db.delete(existing)

    fields = ResumeFields(
        resume_id=resume_id,
        name=parsed.get("name"),
        phone=parsed.get("phone"),
        id_card=parsed.get("id_card"),
        email=parsed.get("email"),
        education=normalize_education(parsed.get("education")),
        school=parsed.get("school"),
        major=parsed.get("major"),
        graduation_year=parsed.get("graduation_year"),
        work_experience=parsed.get("work_experience"),
        project_experience=parsed.get("project_experience"),
        skills=parsed.get("skills"),
        is_duplicate=is_dup,
    )
    db.add(fields)

    # 5. 存入向量库
    if not is_dup:
        vector_id = dedup.add_resume(resume_id, dedup_text)
        fields.vector_id = vector_id

    db.commit()
    db.refresh(fields)

    msg = "解析成功"
    if is_dup:
        msg = f"解析成功，但与简历 ID={dup_id} 重复（相似度 {score:.2f}）"

    return {"resume_id": resume_id, "status": resume.status, "fields": fields, "message": msg}


@router.get("/{resume_id}/desensitized", response_model=ResumeFieldsOut)
def get_desensitized(resume_id: int, db: Session = Depends(get_db)):
    """获取脱敏后的简历字段。"""
    fields = db.query(ResumeFields).filter(ResumeFields.resume_id == resume_id).first()
    if not fields:
        raise HTTPException(404, "简历字段不存在，请先解析")
    # 脱敏
    raw_data = {
        "phone": fields.phone,
        "id_card": fields.id_card,
        "email": fields.email,
    }
    masked = desensitize(raw_data)
    fields.phone = masked.get("phone")
    fields.id_card = masked.get("id_card")
    fields.email = masked.get("email")
    return fields
