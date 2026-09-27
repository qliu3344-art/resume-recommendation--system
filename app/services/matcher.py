"""双层人岗匹配：门槛过滤 + 加权融合。

两层在业务上的角色不对等：关键词层是准入器（输出「谁有资格」），语义层是
排序器（输出「谁更像」）。排序问题的前提是候选集合是对的——如果两路各自
召回再融合，「学历差两级但技能高度相关」的人会进候选池，然后靠高语义分排
在前面，业务上他根本不该出现。所以准入必须在排序之前。

关键词层内部还要再分两类：
  门槛项（学历等级、工作年限）——二值判定。不达标直接淘汰，达标也不加分，
    它只是入场券，所以不进加权公式。
  软性项（技能命中率）——连续值，命中的要求技能数 / 要求技能总数。
所以通过门槛的候选人，关键词分实际上就是技能命中率。

最终分 = 0.4 × 技能命中率 + 0.6 × 语义相似度。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.job import Job
from app.models.resume import ResumeFields
from app.services.ai_extractor import structure_job_description
from app.services.embedding import embed_text
from app.services.feature_text import build_job_text
from app.services.normalize import collect_resume_skills, education_to_level

_pgvector_version: str | None = None


def _version_at_least(version: str, target: tuple[int, int, int]) -> bool:
    parts = []
    for chunk in (version or "").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    parts += [0] * (3 - len(parts))
    return tuple(parts[:3]) >= target


def _supports_iterative_scan(db: Session) -> bool:
    """迭代扫描是 pgvector 0.8.0 才有的补丁，低版本要跳过设置。"""
    global _pgvector_version
    if _pgvector_version is None:
        row = db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).first()
        _pgvector_version = row[0] if row else ""
    return _version_at_least(_pgvector_version, (0, 8, 0))


def _apply_hnsw_settings(db: Session) -> None:
    """本次检索的 HNSW 运行时参数（事务级）。

    迭代扫描治的是「过滤后结果不足」，不是「不准」：索引默认先取 ef_search
    个候选再拿 WHERE 去筛，过滤选择性一低就凑不满 K。开了之后一批候选不够
    就继续扫，直到凑够或撞上 max_scan_tuples 上限。上限要按 P95 延迟预算调，
    不能只盯召回。
    """
    db.execute(text(f"SET LOCAL hnsw.ef_search = {int(settings.HNSW_EF_SEARCH)}"))
    if _supports_iterative_scan(db):
        db.execute(
            text(f"SET LOCAL hnsw.max_scan_tuples = {int(settings.HNSW_MAX_SCAN_TUPLES)}")
        )
        db.execute(
            text(f"SET LOCAL hnsw.iterative_scan = '{settings.HNSW_ITERATIVE_SCAN}'")
        )


def _serialize_gates(requirements: dict) -> tuple[int, int]:
    """把岗位的硬性要求转成数据库层的门槛值。

    学历落成 0–5 的等级、年限落成月数，两者都是入库前算好的索引列，所以
    这一步能在数据库层用 B-tree 先粗筛，不必把全表拉进 Python 再判断。
    """
    required_education = requirements.get("min_education") or ""
    min_level = education_to_level(required_education) if required_education else 0
    try:
        min_months = int(float(requirements.get("min_years") or 0) * 12)
    except (TypeError, ValueError):
        min_months = 0
    return min_level, min_months


def refresh_job_vector(db: Session, job: Job) -> list[float]:
    """返回岗位向量；库里没有才算一次。

    岗位描述太短（HR 只写了两行）时先让 LLM 结构化成与简历侧同一套字段
    形态：两侧文本形态不对齐会让向量分布产生系统性偏差，对齐是语义召回率
    的前提。不能让质量差的输入静默地产生质量差的匹配结果。
    """
    if job.retrieval_vec is not None:
        return list(job.retrieval_vec)

    description = (job.description or "").strip()
    if len(description) < settings.JOB_DESCRIPTION_MIN_LEN:
        description = structure_job_description(
            job.title, description, job.requirements or {}
        )

    job.retrieval_vec = embed_text(build_job_text(description, job.requirements or {}))
    db.flush()
    return list(job.retrieval_vec)


def _skill_score(
    required_skills: list, resume_skills, project_experience
) -> tuple[float, str]:
    """技能命中率 = 命中的要求技能数 / 要求技能总数。

    两侧都过归一化和别名表，否则「J2EE」和「Java」会被算成两个技能。简历
    侧还要合并项目经历的技术栈——只看 skills 字段会漏掉一半能力信号，而且
    会系统性偏袒「会包装自己」的候选人。
    """
    if not required_skills:
        return 1.0, "岗位未设技能要求"

    required = collect_resume_skills(required_skills, None)
    owned = collect_resume_skills(resume_skills, project_experience)
    hit = len(required & owned)
    return hit / len(required), f"技能 {hit}/{len(required)} 命中"


def match_job_to_resumes(db: Session, job: Job, top_k: int = 20) -> list[dict]:
    """双层匹配：门槛过滤 + 语义排序 + 加权融合，返回推荐列表。"""
    requirements = job.requirements or {}
    min_level, min_months = _serialize_gates(requirements)
    required_skills = requirements.get("required_skills") or []

    query_vec = refresh_job_vector(db, job)
    _apply_hnsw_settings(db)

    # 过滤和向量排序在同一条 SQL 里相遇——过滤走 B-tree 索引，排序走向量
    # 算子，由执行计划决定怎么组合。拆成两次操作要么凑不满 K，要么得把几万
    # 个 id 塞进 IDSelector。
    similarity = ResumeFields.retrieval_vec.max_inner_product(query_vec)
    query = (
        db.query(
            ResumeFields.resume_id,
            ResumeFields.skills,
            ResumeFields.project_experience,
            ResumeFields.education_level,
            ResumeFields.work_months,
            similarity.label("neg_inner_product"),
        )
        .filter(ResumeFields.is_duplicate.is_(False))
        .filter(ResumeFields.retrieval_vec.isnot(None))
    )
    if min_level > 0:
        query = query.filter(ResumeFields.education_level >= min_level)
    if min_months > 0:
        query = query.filter(ResumeFields.work_months >= min_months)

    candidates = (
        query.order_by(similarity).limit(settings.SEMANTIC_SEARCH_MAX_K).all()
    )

    # 岗位没填技能要求时，关键词层退化成常量，0.4/0.6 就没有意义了——这时候
    # 应该直接走纯语义，而不是套用这个公式。权重是为「两层都有信息」的场景调的。
    if required_skills:
        w_keyword, w_semantic = (
            settings.KEYWORD_MATCH_WEIGHT,
            settings.SEMANTIC_MATCH_WEIGHT,
        )
    else:
        w_keyword, w_semantic = 0.0, 1.0

    results = []
    for row in candidates:
        keyword_score, skill_detail = _skill_score(
            required_skills, row.skills, row.project_experience
        )
        semantic_score = -float(row.neg_inner_product)
        total = w_keyword * keyword_score + w_semantic * semantic_score

        results.append({
            "resume_id": row.resume_id,
            "keyword_score": round(keyword_score, 4),
            "semantic_score": round(semantic_score, 4),
            "total_score": round(total, 4),
            # HR 看到 0.85 要能问「他为什么是 0.85」，所以分数必须能拆开讲
            "match_details": {
                "skills": skill_detail,
                "education": f"达标（等级 {row.education_level} ≥ {min_level}）"
                if min_level
                else "岗位未设学历门槛",
                "work_years": f"达标（{row.work_months} 个月 ≥ {min_months} 个月）"
                if min_months
                else "岗位未设年限门槛",
                "semantic": f"语义相似度 {semantic_score:.4f}",
            },
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results[:top_k]
