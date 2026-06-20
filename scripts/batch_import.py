"""批量导入模拟数据到数据库（跳过文件上传，直接写入）。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models.resume import Resume, ResumeFields
from app.models.job import Job
from app.services.dedup import get_dedup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LABEL_DIR = os.path.join(BASE_DIR, "data", "labels")
RESUME_DIR = os.path.join(BASE_DIR, "data", "resumes")


def load_labels():
    with open(os.path.join(LABEL_DIR, "resume_labels.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_jobs():
    with open(os.path.join(LABEL_DIR, "jobs.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def import_resumes(db):
    """批量导入简历数据。"""
    labels = load_labels()
    total = len(labels)
    imported = 0
    skipped = 0

    for item in labels:
        rid = item["id"]
        fields_data = item["fields"]

        # 检查是否已存在
        existing = db.query(Resume).filter(Resume.id == rid).first()
        if existing:
            skipped += 1
            continue

        # 读取文本文件
        txt_path = os.path.join(RESUME_DIR, f"resume_{rid:04d}.txt")
        raw_text = ""
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

        # 创建 Resume 记录
        resume = Resume(
            id=rid,
            filename=f"resume_{rid:04d}.txt",
            file_path=txt_path,
            raw_text=raw_text,
            parsed_data=fields_data,
            status="verified",
        )
        db.add(resume)

        # 创建 ResumeFields 记录
        rf = ResumeFields(
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
            skills=fields_data.get("skills"),
            is_duplicate=False,
        )
        db.add(rf)
        imported += 1

    db.commit()
    print(f"  ✅ 简历导入完成: {imported} 条新增, {skipped} 条跳过")
    return imported


def import_jobs(db):
    """批量导入岗位数据。"""
    jobs = load_jobs()
    imported = 0
    skipped = 0

    for job_data in jobs:
        jid = job_data["id"]
        existing = db.query(Job).filter(Job.id == jid).first()
        if existing:
            skipped += 1
            continue

        j = Job(
            id=jid,
            title=job_data["title"],
            description=job_data["description"],
            requirements=job_data["requirements"],
        )
        db.add(j)
        imported += 1

    db.commit()
    print(f"  ✅ 岗位导入完成: {imported} 条新增, {skipped} 条跳过")
    return imported


def build_vectors(db):
    """为非重复简历构建向量索引。"""
    dedup = get_dedup()
    fields_list = (
        db.query(ResumeFields)
        .filter(ResumeFields.is_duplicate == False)
        .filter(ResumeFields.vector_id == None)
        .all()
    )
    print(f"  📊 需要向量化 {len(fields_list)} 份简历...")

    texts = []
    resume_ids = []

    for rf in fields_list:
        work_companies = " ".join(
            w.get("company", "") for w in (rf.work_experience or [])
        )
        skills_str = " ".join(rf.skills or [])
        text = f"{rf.name or ''} {rf.education or ''} {rf.school or ''} {rf.major or ''} {work_companies} {skills_str}"
        texts.append(text)
        resume_ids.append(rf.resume_id)

    # 批量向量化（每批6条，DashScope限制）
    batch_size = 6
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_ids = resume_ids[i : i + batch_size]
        try:
            dedup.add_batch(batch_ids, batch_texts)
            # 更新 vector_id
            for j, rid in enumerate(batch_ids):
                rf = db.query(ResumeFields).filter(ResumeFields.resume_id == rid).first()
                if rf:
                    rf.vector_id = str(i + j)
        except Exception as e:
            print(f"    ⚠️ 批次 {i}-{i+len(batch_texts)} 失败: {e}")
            # 逐条重试
            for text, rid in zip(batch_texts, batch_ids):
                try:
                    vid = dedup.add_resume(rid, text)
                    rf = db.query(ResumeFields).filter(ResumeFields.resume_id == rid).first()
                    if rf:
                        rf.vector_id = vid
                except Exception as e2:
                    print(f"      ⚠️ 简历 {rid} 跳过: {e2}")

        done = min(i + batch_size, len(texts))
        if done % 100 < batch_size:
            db.commit()
            print(f"    ... 已处理 {done}/{len(texts)}")

    db.commit()
    print(f"  ✅ 向量索引构建完成")


def mark_duplicates(db):
    """标记重复简历。"""
    dup_path = os.path.join(LABEL_DIR, "duplicate_groups.json")
    with open(dup_path, "r", encoding="utf-8") as f:
        dup_groups = json.load(f)

    for source_id, dup_id in dup_groups:
        rf = db.query(ResumeFields).filter(ResumeFields.resume_id == dup_id).first()
        if rf:
            rf.is_duplicate = True

    db.commit()
    print(f"  ✅ 已标记 {len(dup_groups)} 组重复简历")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("📝 批量导入模拟数据...")
        print("\n1. 导入简历:")
        import_resumes(db)

        print("\n2. 导入岗位:")
        import_jobs(db)

        print("\n3. 标记重复简历:")
        mark_duplicates(db)

        print("\n4. 构建向量索引:")
        build_vectors(db)

        print("\n🎉 批量导入完成！")
    finally:
        db.close()
