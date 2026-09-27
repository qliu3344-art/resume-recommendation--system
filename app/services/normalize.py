"""字段归一化模块：把非标准字段值统一成标准值，供评估和推荐共享。

问题背景：评估脚本用严格 == 比对、匹配引擎用 dict.get() 查表，
两者对「不规范值」（如「硕士在读」「MBA」）的容忍度不一致，导致：
  - 评估层面：假阴性（语义相同但字符串不同被判错）
  - 推荐层面：真错误（查表查不到返回 0，学历被误判为不满足）
根本解法：学历在入库前统一归一化，评估和匹配共享同一套等级标准。

同一套理由适用于技能和工作年限：三者的归一化结果都在入库前算好并落成
数据库列（见 models/resume.py），匹配时直接参与 SQL 门槛过滤。
"""
import re
from datetime import datetime

# 学历别名表：非标准表述 → 标准等级词
EDUCATION_ALIASES = {
    "硕士研究生": "硕士",
    "硕士在读": "硕士",
    "研究生": "硕士",
    "MBA": "硕士",
    "硕士毕业": "硕士",
    "大学本科": "本科",
    "本科在读": "本科",
    "本科肄业": "本科",
    "学士": "本科",
    "本科生": "本科",
    "大专": "专科",
    "大学专科": "专科",
    "博士研究生": "博士",
    "博士在读": "博士",
    "PhD": "博士",
}

# 学历等级映射：等级词 → 数字（越大越高）
EDUCATION_LEVELS = {
    "高中": 1, "中专": 1,
    "专科": 2, "大专": 2,
    "本科": 3,
    "硕士": 4, "研究生": 4,
    "博士": 5,
}

# 技能别名表：同义词归并到同一个规范名。
# 不做归并的话，候选人写「J2EE」、岗位要求写「Java」，会被算成两个技能，
# 命中率被系统性低估——这不是判错，是判空。
SKILL_ALIASES = {
    "j2ee": "java",
    "javaee": "java",
    "java ee": "java",
    "springboot": "spring boot",
    "spring-boot": "spring boot",
    "springcloud": "spring cloud",
    "spring-cloud": "spring cloud",
    "k8s": "kubernetes",
    "vuejs": "vue",
    "vue.js": "vue",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node",
    "node.js": "node",
    "golang": "go",
    "postgres": "postgresql",
    "mssql": "sql server",
}


def normalize_education(raw: str | None) -> str:
    """把学历的非标准表述归一化成标准等级词。

    「硕士在读」→「硕士」，「MBA」→「硕士」，「本科肄业」→「本科」。
    未命中别名表的原样返回（保留原始信息，避免信息丢失）。
    """
    if not raw:
        return ""
    value = str(raw).strip()
    return EDUCATION_ALIASES.get(value, value)


def education_to_level(edu: str | None) -> int:
    """学历转等级，带包含匹配兜底。

    先精确查表；查不到则做包含匹配（如「硕士学历」→「硕士」→ 4，
    「本科及以上」→「本科」→ 3）。最终兜底返回 0（不满足任何等级）。
    """
    if not edu:
        return 0
    normalized = normalize_education(edu)
    if normalized in EDUCATION_LEVELS:
        return EDUCATION_LEVELS[normalized]
    # 兜底：包含匹配，长关键词优先，避免单字误配
    for key in sorted(EDUCATION_LEVELS, key=len, reverse=True):
        if key in normalized:
            return EDUCATION_LEVELS[key]
    return 0


def normalize_skill(raw: str | None) -> str:
    """技能归一化：统一小写、压空白、别名归并。

    「Java」和「java」、「J2EE」和「Java」都归到同一个规范名。
    """
    if not raw:
        return ""
    value = re.sub(r"\s+", " ", str(raw).strip().lower())
    return SKILL_ALIASES.get(value, value)


def normalize_skills(raw_list) -> set[str]:
    """把技能列表归一化成规范名集合。"""
    result = set()
    for item in raw_list or []:
        normalized = normalize_skill(item)
        if normalized:
            result.add(normalized)
    return result


def collect_resume_skills(skills, project_experience) -> set[str]:
    """合并两处技能来源：skills 字段 + 项目经历里的 tech_stack。

    候选人技能列表通常只写 5–8 个核心技能，真实用过的技术往往藏在项目
    经历的技术栈里。只看 skills 字段会漏掉一半能力信号，而且会系统性
    偏袒「会包装自己」的候选人。
    """
    merged = normalize_skills(skills)
    for proj in project_experience or []:
        if isinstance(proj, dict):
            merged |= normalize_skills(proj.get("tech_stack"))
    return merged


# ---------- 工作年限：有效月数累计 ----------

_PERIOD_RE = re.compile(
    r"(\d{4})\s*[./\-年]?\s*(\d{1,2})?\s*[月]?\s*[-—~～至到]+\s*"
    r"(\d{4}|至今|现在|今)\s*[./\-年]?\s*(\d{1,2})?"
)
_PRESENT_TOKENS = {"至今", "现在", "今"}


def _month_index(year: int, month: int | None, *, is_start: bool) -> int:
    """把 (年, 月) 转成月序号，方便做区间运算。

    月份缺失时取端点：起点缺月按 1 月、终点缺月按 12 月。
    """
    if not month or not 1 <= month <= 12:
        month = 1 if is_start else 12
    return year * 12 + (month - 1)


def _merge_month_intervals(intervals: list[tuple[int, int]]) -> int:
    """合并重叠区间，返回区间总长度（月）。"""
    if not intervals:
        return 0
    ordered = sorted(intervals)
    total = 0
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
    return total + (cur_end - cur_start)


def work_experience_months(work_experience) -> int:
    """从工作经历累计有效工作月数，并扣除重叠区间。

    为什么不是「最晚结束 − 最早开始」：那样会把 gap year 算成工作经验
    （高估）。为什么不是各段简单求和：并行经历会被重复计算（也是高估）。
    扣除重叠的累计月数才是真实工龄。

    period 解析不出来的段直接跳过、按 0 计——宁可不算，也不凭段数估一个
    假数出来，否则「门槛」二字就落空了。
    """
    intervals: list[tuple[int, int]] = []
    for exp in work_experience or []:
        if not isinstance(exp, dict):
            continue
        period = str(exp.get("period") or "")
        if not period:
            continue
        match = _PERIOD_RE.search(period)
        if not match:
            continue

        start = _month_index(
            int(match.group(1)), int(match.group(2)) if match.group(2) else None,
            is_start=True,
        )
        end_token = match.group(3)
        if end_token in _PRESENT_TOKENS:
            now = datetime.now()
            end = now.year * 12 + (now.month - 1)
        else:
            end = _month_index(
                int(end_token), int(match.group(4)) if match.group(4) else None,
                is_start=False,
            )

        if end > start:
            intervals.append((start, end))

    return _merge_month_intervals(intervals)
