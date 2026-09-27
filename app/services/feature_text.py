"""两份特征文本。

去重和检索的「相似」定义根本不同：同一个人换了工作、更新了技能，简历变了，
但仍然是同一个人——去重应该判重；而两个不同的人可能技能高度相似——检索
应该召回。用同一份向量做两件事，必然有一件事是错的。这不是优化，是设计上
的必需。

拼接模板固定（固定字段、固定顺序、固定分隔）：顺序一变向量就变，历史索引
和新写入的向量就不在同一个分布里了。这里的一致性是为了系统稳定，不是为了
模型精度。
"""
from app.services.normalize import collect_resume_skills


def _clean(value) -> str:
    return str(value).strip() if value is not None else ""


def build_dedup_text(fields: dict) -> str:
    """去重特征：稳定锚点 —— 姓名 + 学校 + 公司。

    判重问的是「这是不是同一个人」，所以只取短时间内不会变的身份信号。
    改技能、加项目不该影响判重，所以能力信号一律不进来。
    """
    parts = [_clean(fields.get("name")), _clean(fields.get("school"))]

    companies: list[str] = []
    for exp in fields.get("work_experience") or []:
        if isinstance(exp, dict):
            company = _clean(exp.get("company"))
            # 同一家公司待过两段（离职又回去），锚点里只应出现一次
            if company and company not in companies:
                companies.append(company)

    parts.extend(companies)
    return " ".join(p for p in parts if p)


def build_retrieval_text(fields: dict) -> str:
    """检索特征：能力信号 —— 学历 + 专业 + 技能 + 项目技术栈 + 工作经历。

    刻意写成类自然语言的描述，而不是 key-value 拼接。语义层的另一侧是岗位
    描述（自然语言长文本），两侧文本形态不对齐会让向量分布产生系统性偏差。
    「像一个人在介绍自己」是为了让两侧落在同一个文本分布里——这是语义召回
    率的前提。

    学校不在这里：它同时是身份锚点，放进检索会往排序里注入学历出身偏差，
    而岗位要的是能力方向匹配。
    """
    sentences: list[str] = []

    education = _clean(fields.get("education"))
    major = _clean(fields.get("major"))
    if education or major:
        sentences.append("，".join(p for p in (education, major) if p) + "。")

    # 技能从 skills 字段和项目经历的技术栈两处合并（见 normalize.collect_resume_skills）
    skills = sorted(collect_resume_skills(
        fields.get("skills"), fields.get("project_experience")
    ))
    if skills:
        sentences.append("熟练掌握 " + "、".join(skills) + "。")

    worked = []
    for exp in fields.get("work_experience") or []:
        if not isinstance(exp, dict):
            continue
        company = _clean(exp.get("company"))
        position = _clean(exp.get("position"))
        label = " ".join(p for p in (company, position) if p)
        if label:
            worked.append(label)
    if worked:
        sentences.append("曾在 " + "、".join(worked) + " 任职。")

    projects = []
    for proj in fields.get("project_experience") or []:
        if isinstance(proj, dict):
            name = _clean(proj.get("project_name"))
            if name:
                projects.append(name)
    if projects:
        sentences.append("参与过 " + "、".join(projects) + " 等项目。")

    return " ".join(sentences)


def build_job_text(description: str | None, requirements: dict | None = None) -> str:
    """岗位侧特征文本。

    岗位描述本身就是自然语言，正常情况下直接用。只有当它质量太差（HR 只写
    了两行，提不出技术栈）时，才由上层先用 LLM 结构化成同一套字段形态再拼
    ——两侧必须落在同一个文本分布里。
    """
    text = _clean(description)
    if text:
        return text

    # 描述为空时退到结构化要求，至少不让语义层拿到空串
    req = requirements or {}
    parts = []
    for key in ("min_education", "min_years"):
        if req.get(key):
            parts.append(f"{key} {req[key]}")
    skills = req.get("required_skills") or []
    if skills:
        parts.append("技能 " + "、".join(str(s) for s in skills))
    return " ".join(parts)
