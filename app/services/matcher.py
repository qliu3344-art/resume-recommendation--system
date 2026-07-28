from sqlalchemy.orm import Session

from app.config import settings
from app.models.resume import ResumeFields
from app.models.job import Job
from app.services.dedup import get_dedup


# 学历等级映射
EDUCATION_LEVELS = {
    "高中": 1, "中专": 1,
    "专科": 2, "大专": 2,
    "本科": 3,
    "硕士": 4, "研究生": 4,
    "博士": 5,
}


def keyword_match(resume_fields: ResumeFields, requirements: dict) -> tuple[float, dict]:
    """第一层：关键词精确匹配。
    检查硬性条件：学历、工作年限、必须技能。
    返回: (得分 0-1, 匹配详情)
    """
    if not requirements:
        return 1.0, {"reason": "无硬性要求"}

    scores = []
    details = {}

    # 学历匹配
    req_edu = requirements.get("min_education", "")
    if req_edu:
        req_level = EDUCATION_LEVELS.get(req_edu, 0)
        resume_level = EDUCATION_LEVELS.get(resume_fields.education or "", 0)
        if resume_level >= req_level:
            scores.append(1.0)
            details["education"] = f"满足（{resume_fields.education} >= {req_edu}）"
        else:
            scores.append(0.0)
            details["education"] = f"不满足（{resume_fields.education} < {req_edu}）"

    # 工作年限匹配
    req_years = requirements.get("min_years", 0)
    if req_years > 0:
        work_exp = resume_fields.work_experience or []
        actual_years = len(work_exp)  # 简化：以工作经历段数估算
        if actual_years >= req_years:
            scores.append(1.0)
            details["years"] = f"满足（{actual_years} >= {req_years}）"
        else:
            scores.append(0.0)
            details["years"] = f"不满足（{actual_years} < {req_years}）"

    # 技能匹配 — 合并 skills 和 project_experience 中的 tech_stack
    req_skills = requirements.get("required_skills", [])
    if req_skills:
        resume_skills = set(s.lower() for s in (resume_fields.skills or []))
        # 从项目经历中提取技术栈作为技能补充
        for proj in (resume_fields.project_experience or []):
            for tech in (proj.get("tech_stack") or []):
                resume_skills.add(tech.lower())
        matched = sum(1 for s in req_skills if s.lower() in resume_skills)
        skill_score = matched / len(req_skills)
        scores.append(skill_score)
        details["skills"] = f"{matched}/{len(req_skills)} 命中"

    if not scores:
        return 1.0, {"reason": "无可评估的硬性要求"}

    avg_score = sum(scores) / len(scores)
    return avg_score, details


def semantic_match(job_description: str, top_k: int = 20) -> list[dict]:
    """第二层：RAG 语义检索，返回最相似的简历 ID 和分数。"""
    dedup = get_dedup()
    return dedup.search_similar(job_description, top_k=top_k)


def match_job_to_resumes(
    db: Session, job: Job, top_k: int = 20
) -> list[dict]:
    """双层匹配：关键词过滤 + 语义排序，返回推荐列表。"""
    requirements = job.requirements or {}
    description = job.description or job.title

    # 第一层：获取所有非重复简历，做关键词过滤
    all_fields = (
        db.query(ResumeFields)
        .filter(ResumeFields.is_duplicate == False)
        .all()
    )

    keyword_passed = []
    keyword_scores = {}
    for rf in all_fields:
        score, details = keyword_match(rf, requirements)
        if score >= 0.5:  # 关键词通过率 >= 50%
            keyword_passed.append(rf.resume_id)
            keyword_scores[rf.resume_id] = (score, details)

    if not keyword_passed:
        return []

    # 第二层：语义检索（动态 k = 全部关键词通过者，避免漏算）
    semantic_results = semantic_match(description, top_k=len(keyword_passed))
    semantic_scores = {r["resume_id"]: r["score"] for r in semantic_results}

    # 综合评分
    final_results = []
    for resume_id in keyword_passed:
        kw_score = keyword_scores[resume_id][0]
        sem_score = semantic_scores.get(resume_id, 0.0)
        total = (
            settings.KEYWORD_MATCH_WEIGHT * kw_score
            + settings.SEMANTIC_MATCH_WEIGHT * sem_score
        )
        final_results.append({
            "resume_id": resume_id,
            "keyword_score": round(kw_score, 4),
            "semantic_score": round(sem_score, 4),
            "total_score": round(total, 4),
            "match_details": keyword_scores[resume_id][1],
        })

    # 按综合得分排序
    final_results.sort(key=lambda x: x["total_score"], reverse=True)
    return final_results[:top_k]
