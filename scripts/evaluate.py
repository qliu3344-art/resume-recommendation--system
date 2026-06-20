"""评估脚本：计算解析准确率、去重识别率、匹配召回率和准确率。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.resume import Resume, ResumeFields
from app.models.job import Job, JobMatch

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LABEL_DIR = os.path.join(BASE_DIR, "data", "labels")


def load_labels() -> dict:
    """加载标注数据。"""
    with open(os.path.join(LABEL_DIR, "resume_labels.json"), "r", encoding="utf-8") as f:
        labels = json.load(f)
    return {item["id"]: item["fields"] for item in labels}


def load_dup_groups() -> list:
    """加载重复组。"""
    with open(os.path.join(LABEL_DIR, "duplicate_groups.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_extraction(db: Session, sample_size: int = 50):
    """评估 AI 解析准确率。"""
    labels = load_labels()

    fields_list = db.query(ResumeFields).limit(sample_size).all()
    if not fields_list:
        print("⚠️  没有已解析的简历数据，请先运行解析流程")
        return

    check_fields = ["name", "phone", "email", "education", "school", "major", "graduation_year"]
    total_checks = 0
    correct_checks = 0

    for rf in fields_list:
        label = labels.get(rf.resume_id)
        if not label:
            continue
        for field_name in check_fields:
            actual = getattr(rf, field_name, None)
            expected = label.get(field_name)
            if actual is not None and expected is not None:
                total_checks += 1
                if str(actual).strip() == str(expected).strip():
                    correct_checks += 1

    accuracy = correct_checks / total_checks if total_checks > 0 else 0
    print(f"📊 解析准确率评估:")
    print(f"   检查字段: {check_fields}")
    print(f"   评估样本: {len(fields_list)} 份")
    print(f"   总检查项: {total_checks}")
    print(f"   正确项数: {correct_checks}")
    print(f"   准确率:   {accuracy:.1%}")
    return accuracy


def evaluate_dedup(db: Session):
    """评估去重识别准确率。"""
    dup_groups = load_dup_groups()

    correct = 0
    total = len(dup_groups)

    for source_id, dup_id in dup_groups:
        dup_fields = db.query(ResumeFields).filter(ResumeFields.resume_id == dup_id).first()
        if dup_fields and dup_fields.is_duplicate:
            correct += 1

    recall = correct / total if total > 0 else 0
    print(f"\n📊 去重识别评估:")
    print(f"   重复组数: {total}")
    print(f"   正确识别: {correct}")
    print(f"   召回率:   {recall:.1%}")
    return recall


def evaluate_matching(db: Session):
    """评估匹配效果（基于关键词和语义得分分布）。"""
    all_matches = db.query(JobMatch).all()
    if not all_matches:
        print("⚠️  没有匹配数据，请先运行匹配流程")
        return

    total = len(all_matches)
    high_score = sum(1 for m in all_matches if m.total_score >= 0.6)
    mid_score = sum(1 for m in all_matches if 0.3 <= m.total_score < 0.6)

    print(f"\n📊 匹配效果评估:")
    print(f"   总匹配数:     {total}")
    print(f"   高匹配(≥0.6): {high_score} ({high_score/total:.1%})")
    print(f"   中匹配(0.3-0.6): {mid_score} ({mid_score/total:.1%})")
    print(f"   低匹配(<0.3): {total - high_score - mid_score} ({(total - high_score - mid_score)/total:.1%})")

    avg_keyword = sum(m.keyword_score for m in all_matches) / total
    avg_semantic = sum(m.semantic_score for m in all_matches) / total
    avg_total = sum(m.total_score for m in all_matches) / total
    print(f"   平均关键词分: {avg_keyword:.3f}")
    print(f"   平均语义分:   {avg_semantic:.3f}")
    print(f"   平均综合分:   {avg_total:.3f}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("=" * 50)
        print("智能简历推荐系统 - 评估报告")
        print("=" * 50)
        evaluate_extraction(db)
        evaluate_dedup(db)
        evaluate_matching(db)
        print("\n" + "=" * 50)
    finally:
        db.close()
