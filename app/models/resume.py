from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column, Integer, SmallInteger, String, Text, DateTime, Boolean, ForeignKey, JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.config import settings
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

    # 级联删除：删除简历时结构化字段和匹配记录一起走。删除是真正的 DELETE，
    # 空间回收到 VACUUM——不需要自研「标记 + 延迟回收」那一套。
    fields = relationship(
        "ResumeFields", back_populates="resume", uselist=False,
        cascade="all, delete-orphan",
    )
    matches = relationship(
        "JobMatch", back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeFields(Base):
    __tablename__ = "resume_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    id_card = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    education = Column(String(50), nullable=True)
    school = Column(String(100), nullable=True)
    major = Column(String(100), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    work_experience = Column(JSON, nullable=True)
    project_experience = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)

    # 门槛项：入库前算好并落成列。落成列是为了让「学历达标 且 年限达标」这一步
    # 能走 B-tree 索引在数据库层先粗筛，而不是把全表拉进 Python 再判断
    # （归一化在入库前完成，粗筛前置到数据库层）
    education_level = Column(SmallInteger, nullable=False, default=0)
    work_months = Column(Integer, nullable=False, default=0)

    # 两份特征文本各一个向量。去重和检索的「相似」定义不同，共用一份必然
    # 有一件事是错的：
    #   dedup_vec     = 稳定锚点（姓名+学校+公司），走精确检索，不建索引
    #   retrieval_vec = 能力信号（学历+专业+技能+项目技术栈+工作经历），建 HNSW
    dedup_vec = Column(Vector(settings.EMBEDDING_DIM), nullable=True)
    retrieval_vec = Column(Vector(settings.EMBEDDING_DIM), nullable=True)

    is_duplicate = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    resume = relationship("Resume", back_populates="fields")
