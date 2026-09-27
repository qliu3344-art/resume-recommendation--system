"""批量导入模拟数据到数据库（跳过文件上传，直接写入）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text

from app.database import SessionLocal
from app.models.resume import Resume, ResumeFields
from app.models.job import Job
from app.services.dedup import check_duplicate
from app.services.embedding import embed_texts
from app.services.feature_text import build_dedup_text, build_retrieval_text
from app.services.normalize import education_to_level, work_experience_months
from app.services.matcher import refresh_job_vector

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LABEL_DIR = os.path.join(BASE_DIR, "data", "labels")
RESUME_DIR = os.path.join(BASE_DIR, "data", "resumes")

# 每轮处理的简历数。每份要算两份特征文本，分批是为了让进度可见、事务别太长
CHUNK_SIZE = 50


def load_labels():
    with open(os.path.join(LABEL_DIR, "resume_labels.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_jobs():
    with open(os.path.join(LABEL_DIR, "jobs.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _fields_payload(fields_data: dict) -> dict:
    """把结构化字段整理成特征文本构造函数要的形态。"""
    return {
        "name": fields_data.get("name"),
        "education": fields_data.get("education"),
        "school": fields_data.get("school"),
        "major": fields_data.get("major"),
        "work_experience": fields_data.get("work_experience"),
        "project_experience": fields_data.get("project_experience"),
        "skills": fields_data.get("skills"),
    }


def _payload_of(rf: ResumeFields) -> dict:
    """从 ORM 记录取出特征文本要的字段。"""
    return {
        "name": rf.name,
        "education": rf.education,
        "school": rf.school,
        "major": rf.major,
        "work_experience": rf.work_experience,
        "project_experience": rf.project_experience,
        "skills": rf.skills,
    }


def import_resumes(db):
    """批量导入简历数据。"""
    labels = load_labels()
    imported = 0
    skipped = 0

    for item in labels:
        rid = item["id"]
        fields_data = item["fields"]

        if db.query(Resume).filter(Resume.id == rid).first():
            skipped += 1
            continue

        txt_path = os.path.join(RESUME_DIR, f"resume_{rid:04d}.txt")
        raw_text = ""
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

        db.add(Resume(
            id=rid,
            filename=f"resume_{rid:04d}.txt",
            file_path=txt_path,
            raw_text=raw_text,
            parsed_data=fields_data,
            status="verified",
        ))

        # 门槛项在入库前算好并落成列——匹配时才能走索引在数据库层粗筛
        db.add(ResumeFields(
            resume_id=rid,
            name=fields_data.get("name"),
            phone=fields_data.get("phone"),
            id_card=fields_data.get("id_card"),
            email=fields_data.get("email"),
            education=fields_data.get("education"),
            school=fields_data.get("school"),
            major=fields_data.get("major"),
            graduation_year=fields_data.get("graduation_year"),
            work_experience=fields_data.get("work_experience"),
            project_experience=fields_data.get("project_experience"),
            skills=fields_data.get("skills"),
            education_level=education_to_level(fields_data.get("education")),
            work_months=work_experience_months(fields_data.get("work_experience")),
            is_duplicate=False,
        ))
        imported += 1

    db.commit()
    print(f"  ✅ 简历导入完成: {imported} 条新增, {skipped} 条跳过")
    return imported


def import_jobs(db):
    """批量导入岗位数据，并顺带算好岗位向量。"""
    jobs = load_jobs()
    imported = 0
    skipped = 0

    for job_data in jobs:
        jid = job_data["id"]
        if db.query(Job).filter(Job.id == jid).first():
            skipped += 1
            continue

        job = Job(
            id=jid,
            title=job_data["title"],
            description=job_data["description"],
            requirements=job_data["requirements"],
        )
        db.add(job)
        db.flush()
        refresh_job_vector(db, job)
        imported += 1

    db.commit()
    print(f"  ✅ 岗位导入完成: {imported} 条新增, {skipped} 条跳过")
    return imported


def build_vectors(db):
    """为简历构建两份特征向量：去重锚点 + 检索能力信号。"""
    pending = (
        db.query(ResumeFields)
        .filter(ResumeFields.retrieval_vec.is_(None))
        .order_by(ResumeFields.id)
        .all()
    )
    if not pending:
        print("  ✅ 所有简历的向量都已就绪")
        return

    print(f"  📊 需要向量化 {len(pending)} 份简历（每份两份特征文本）...")

    for start in range(0, len(pending), CHUNK_SIZE):
        chunk = pending[start : start + CHUNK_SIZE]
        # 收集本轮的「行 + 哪一侧 + 文本」，空文本直接跳过——向量化空串没有
        # 意义，而且会让整批 API 调用失败
        pending_vectors = []
        for rf in chunk:
            payload = _payload_of(rf)
            for side, text in (
                ("dedup", build_dedup_text(payload)),
                ("retrieval", build_retrieval_text(payload)),
            ):
                if text.strip():
                    pending_vectors.append((rf, side, text))

        vectors = embed_texts([text for _, _, text in pending_vectors])
        for (rf, side, _), vector in zip(pending_vectors, vectors):
            if side == "dedup":
                rf.dedup_vec = vector
            else:
                rf.retrieval_vec = vector

        db.commit()
        done = min(start + CHUNK_SIZE, len(pending))
        print(f"    ... 已处理 {done}/{len(pending)}")

    print("  ✅ 向量构建完成")


def mark_duplicates(db):
    """跑一遍真实去重，把引擎判为重复的简历标记出来。

    刻意不照着标注文件直接打标：那样评估就成了自证——标注说是重复、打标
    也说是重复，召回率必然 100%。这里让引擎自己判，标注文件只用于评估。
    两者分开，去重召回率才是一个有意义的数。
    """
    with open(os.path.join(LABEL_DIR, "duplicate_groups.json"), "r", encoding="utf-8") as f:
        dup_groups = json.load(f)

    flagged = 0
    for _source_id, dup_id in dup_groups:
        rf = db.query(ResumeFields).filter(ResumeFields.resume_id == dup_id).first()
        if rf is None:
            continue
        payload = _payload_of(rf)
        is_dup, _match_id, _score = check_duplicate(
            db, build_dedup_text(payload), exclude_resume_id=dup_id
        )
        if is_dup:
            rf.is_duplicate = True
            flagged += 1

    db.commit()
    print(f"  ✅ {len(dup_groups)} 组标注重复中，引擎判出 {flagged} 组")


def reset_sequences(db):
    """把自增序列拨到 max(id) 之后。

    导入是带显式 id 写入的（Resume(id=rid) / Job(id=jid)）。MySQL 的
    AUTO_INCREMENT 会跟着显式插入推进，PostgreSQL 的序列不会——不拨的话
    序列停在 1，之后任何不带 id 的插入（比如接口上传简历）都会撞主键，
    报 duplicate key value violates unique constraint。这是迁移里典型的坑。
    """
    for table in ("resumes", "jobs", "resume_fields", "job_matches"):
        seq = db.execute(
            text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": table}
        ).scalar()
        if not seq:
            continue
        max_id = db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar()
        db.execute(text("SELECT setval(:s, :v)"), {"s": seq, "v": max(max_id, 1)})
    db.commit()
    print("  ✅ 自增序列已对齐到 max(id)")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("📝 批量导入模拟数据...")
        print("\n1. 导入简历:")
        import_resumes(db)

        print("\n2. 导入岗位:")
        import_jobs(db)

        print("\n3. 构建特征向量:")
        build_vectors(db)

        print("\n4. 运行去重:")
        mark_duplicates(db)

        print("\n5. 对齐自增序列:")
        reset_sequences(db)

        print("\n🎉 批量导入完成！")
    finally:
        db.close()
