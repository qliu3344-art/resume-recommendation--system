from sqlalchemy.orm import Session

from app.config import settings
from app.models.resume import ResumeFields
from app.models.job import Job
from app.services.dedup import get_dedup
from app.services.normalize import education_to_level

# 语义检索最大 top_k，避免关键词通过人数过多时检索无意义
SEMANTIC_SEARCH_MAX_K = 200


def _parse_work_years(work_experience: list[dict]) -> float:
    """根据工作经历的 period 字段计算累计工作年限。

    period 格式示例："2020.03-2023.06"、"2021/01-2024/12"、"2020-至今"
    多段经历取最早开始和最晚结束的跨度。
    """
    import re

    if not work_experience:
        return 0.0

    all_starts = []
    all_ends = []

    for exp in work_experience:
        period = exp.get("period", "") if isinstance(exp, dict) else ""
        if not period:
            continue
        # 匹配 "2020.03-2023.06" 或 "2020/01-2024/12" 或 "2020-至今"
        match = re.match(r"(\d{4})[./]?\d{0,2}\s*[-—~至]\s*(\d{4}|至今|现在|现在至今)", period)
        if match:
            all_starts.append(int(match.group(1)))
            end_str = match.group(2)
            if end_str in ("至今", "现在", "现在至今"):
                import datetime
                all_ends.append(datetime.datetime.now().year)
            else:
                all_ends.append(int(end_str))

    if not all_starts:
        # period 无法解析，回退到段数估算（1 段 ≈ 1.5 年）
        return len(work_experience) * 1.5

    return max(all_ends) - min(all_starts)


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
        req_level = education_to_level(req_edu)
        resume_level = education_to_level(resume_fields.education)
        if resume_level >= req_level:
            scores.append(1.0)
            details["education"] = f"满足（{resume_fields.education} >= {req_edu}）"
        else:
            scores.append(0.0)
            details["education"] = f"不满足（{resume_fields.education} < {req_edu}）"

    # 工作年限匹配 — 解析 period 字段计算真实年限
    req_years = requirements.get("min_years", 0)
    if req_years > 0:
        work_exp = resume_fields.work_experience or []
        actual_years = _parse_work_years(work_exp)
        if actual_years >= req_years:
            scores.append(1.0)
            details["years"] = f"满足（{actual_years}年 >= {req_years}年）"
        else:
            scores.append(0.0)
            details["years"] = f"不满足（{actual_years}年 < {req_years}年）"

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

    # 第一层：分页遍历非重复简历，避免大数据量 OOM
    keyword_passed = []
    keyword_scores = {}
    page_size = 500
    offset = 0
    while True:
        batch = (
            db.query(ResumeFields)
            .filter(ResumeFields.is_duplicate == False)
            .order_by(ResumeFields.id)
            .limit(page_size)
            .offset(offset)
            .all()
        )
        if not batch:
            break
        for rf in batch:
            score, details = keyword_match(rf, requirements)
            if score >= 0.5:  # 关键词通过率 >= 50%
                keyword_passed.append(rf.resume_id)
                keyword_scores[rf.resume_id] = (score, details)
        offset += page_size

    if not keyword_passed:
        return []

    # 第二层：语义检索（上限 SEMANTIC_SEARCH_MAX_K，超出无区分度）
    semantic_k = min(len(keyword_passed), SEMANTIC_SEARCH_MAX_K)
    semantic_results = semantic_match(description, top_k=semantic_k)
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
