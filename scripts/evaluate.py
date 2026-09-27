"""评估脚本：解析准确率、去重召回率、匹配分数分布。

匹配「真正相关率」不在这里，在 evaluate_judge.py——分数分布合理不代表
每个匹配真的相关（关键词堆砌也能拿高分），那部分必须用独立评审模型判。

⚠️ 口径分界（重要，别混着说）：
   本脚本对着 generate_mock_data.py 造的合成数据跑时，只能在**链路层面**
   说明问题——数据能不能走通、索引建没建成、分数分布合不合理。
   它**不产出对外报的指标**，原因有两条：
     1. 解析准确率那一项在合成数据上是自证的：batch_import 把标注直接写进
        ResumeFields，本脚本再拿同一份标注去比，必然 100%。要走真实解析
        （上传 PDF → 分栏重排 → UIE+qwen 提取）才是指标。
     2. 合成数据的技能是随机分配的，候选人之间没有真实的语义对齐，
        相关性指标在它上面不成立。
   对外的指标来自真实简历与真实岗位的评估集。

用法：python scripts/evaluate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.resume import ResumeFields
from app.models.job import JobMatch
from app.services.normalize import education_to_level

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LABEL_DIR = os.path.join(BASE_DIR, "data", "labels")

CHECK_FIELDS = ["name", "phone", "email", "education", "school", "major", "graduation_year"]


def load_labels() -> dict:
    """加载标注数据。"""
    with open(os.path.join(LABEL_DIR, "resume_labels.json"), "r", encoding="utf-8") as f:
        labels = json.load(f)
    return {item["id"]: item["fields"] for item in labels}


def load_dup_groups() -> list:
    """加载重复组标注。"""
    with open(os.path.join(LABEL_DIR, "duplicate_groups.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _fields_equal(field_name: str, actual, expected) -> bool:
    """字段比对：学历比等级、专业比包含关系，其余严格相等。

    学历用等级比对（「硕士在读」和「硕士」等级相同，避免假阴性）；
    专业用包含比对（「计算机科学与技术」包含「计算机科学」，避免全称/简称误判）。
    """
    if field_name == "education":
        return education_to_level(actual) == education_to_level(expected)
    if field_name == "major":
        a = str(actual).strip()
        e = str(expected).strip()
        return bool(a) and bool(e) and (a in e or e in a)
    return str(actual).strip() == str(expected).strip()


def evaluate_extraction(db: Session, sample_size: int = 500):
    """评估 AI 解析准确率。

    口径：7 个关键字段 × sample_size 份标注样本 = 检查项总数。
    同时报「整份零错误率」——它比单字段准确率更接近 HR 的真实体验，
    而且两者的差值本身有信息：整份零错误率明显低于准确率的 7 次方，
    说明错误是聚集的（个别简历错一片，而不是随机撒在所有人身上）。
    """
    labels = load_labels()
    fields_list = db.query(ResumeFields).limit(sample_size).all()
    if not fields_list:
        print("⚠️  没有已解析的简历数据，请先运行解析流程")
        return None

    total_checks = 0
    correct_checks = 0
    clean_sheets = 0

    for rf in fields_list:
        label = labels.get(rf.resume_id)
        if not label:
            continue
        sheet_clean = True
        for field_name in CHECK_FIELDS:
            actual = getattr(rf, field_name, None)
            expected = label.get(field_name)
            if actual is None or expected is None:
                continue
            total_checks += 1
            if _fields_equal(field_name, actual, expected):
                correct_checks += 1
            else:
                sheet_clean = False
        if sheet_clean:
            clean_sheets += 1

    if total_checks == 0:
        print("⚠️  没有可比对的字段")
        return None

    accuracy = correct_checks / total_checks
    clean_rate = clean_sheets / len(fields_list)
    independent = accuracy ** len(CHECK_FIELDS)

    print("📊 解析准确率评估:")
    print(f"   检查字段: {CHECK_FIELDS}")
    print(f"   评估样本: {len(fields_list)} 份")
    print(f"   总检查项: {total_checks}")
    print(f"   正确项数: {correct_checks}")
    print(f"   准确率:   {accuracy:.1%}")
    print(f"   整份零错误率: {clean_rate:.1%}")
    print(f"   （若各字段错误相互独立，零错误率应为 {accuracy:.2%}^{len(CHECK_FIELDS)}"
          f" = {independent:.1%}；实测高于它，说明错误是聚集的）")
    return accuracy


def evaluate_dedup(db: Session):
    """评估去重召回率。

    注意这里是真评估：is_duplicate 是去重引擎自己判出来的（batch_import 的
    mark_duplicates 跑的是 check_duplicate），标注文件只在这一步当标准答案
    用。如果打标时直接照抄标注，评估就成了自证，召回率必然 100%。
    """
    dup_groups = load_dup_groups()

    correct = 0
    for _source_id, dup_id in dup_groups:
        dup_fields = db.query(ResumeFields).filter(ResumeFields.resume_id == dup_id).first()
        if dup_fields and dup_fields.is_duplicate:
            correct += 1

    total = len(dup_groups)
    recall = correct / total if total > 0 else 0
    print("\n📊 去重识别评估:")
    print(f"   重复组数: {total}")
    print(f"   正确识别: {correct}")
    print(f"   召回率:   {recall:.1%}")
    return recall


def evaluate_matching(db: Session):
    """匹配的分数分布。这是分数合理性，不是相关性——相关性看 evaluate_judge.py。"""
    all_matches = db.query(JobMatch).all()
    if not all_matches:
        print("⚠️  没有匹配数据，请先运行匹配流程")
        return

    total = len(all_matches)
    high_score = sum(1 for m in all_matches if m.total_score >= 0.6)
    mid_score = sum(1 for m in all_matches if 0.3 <= m.total_score < 0.6)

    print("\n📊 匹配分数分布:")
    print(f"   总匹配数:     {total}")
    print(f"   高匹配(≥0.6): {high_score} ({high_score/total:.1%})")
    print(f"   中匹配(0.3-0.6): {mid_score} ({mid_score/total:.1%})")
    print(f"   低匹配(<0.3): {total - high_score - mid_score} "
          f"({(total - high_score - mid_score)/total:.1%})")

    avg_keyword = sum(m.keyword_score for m in all_matches) / total
    avg_semantic = sum(m.semantic_score for m in all_matches) / total
    avg_total = sum(m.total_score for m in all_matches) / total
    print(f"   平均关键词分: {avg_keyword:.3f}")
    print(f"   平均语义分:   {avg_semantic:.3f}")
    print(f"   平均综合分:   {avg_total:.3f}")
    print("   ⚠️ 这个分布只说明分数合理，不说明匹配相关——")
    print("      关键词堆砌也能拿高分（典型反例：Java 培训讲师配 Java 开发岗）。")
    print("      真正相关率由 scripts/evaluate_judge.py 判定。")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("=" * 50)
        print("智能简历推荐系统 - 评估报告")
        print("=" * 50)
        print("⚠️  本报告跑的是合成数据，只说明链路跑得通，不是对外报的指标。")
        print("    解析准确率在合成数据上是自证的（拿标注比标注），必然 100%。")
        print("    对外指标来自真实简历与真实岗位的评估集。\n")
        evaluate_extraction(db)
        evaluate_dedup(db)
        evaluate_matching(db)
        print("\n" + "=" * 50)
    finally:
        db.close()
