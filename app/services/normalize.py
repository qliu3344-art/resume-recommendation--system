"""字段归一化模块：把非标准字段值统一成标准值，供评估和推荐共享。

问题背景：评估脚本用严格 == 比对、匹配引擎用 dict.get() 查表，
两者对「不规范值」（如「硕士在读」「MBA」）的容忍度不一致，导致：
  - 评估层面：假阴性（语义相同但字符串不同被判错）
  - 推荐层面：真错误（查表查不到返回 0，学历被误判为不满足）
根本解法：学历在入库前统一归一化，评估和匹配共享同一套等级标准。
"""

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
