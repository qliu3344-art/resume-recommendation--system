import json
import os

import dashscope
from dashscope import Generation

from app.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY

# ---------- 第一阶段：PaddleNLP UIE 初筛 ----------

_uie_model = None

UIE_SCHEMA = [
    "姓名", "手机号", "身份证号", "邮箱",
    "学历", "毕业院校", "专业", "毕业年份",
    "公司", "职位", "工作时间",
    "技能",
]


def _get_uie_model():
    """懒加载 UIE 模型（首次调用时下载并缓存）。"""
    global _uie_model
    if _uie_model is None:
        from paddlenlp import Taskflow
        _uie_model = Taskflow(
            "information_extraction",
            schema=UIE_SCHEMA,
            model="uie-base",
        )
    return _uie_model


def extract_with_uie(text: str) -> dict:
    """第一阶段：使用 PaddleNLP UIE 提取简历字段。"""
    ie = _get_uie_model()
    results = ie(text)

    parsed = {}
    if results and len(results) > 0:
        result = results[0]
        parsed["name"] = _extract_first(result, "姓名")
        parsed["phone"] = _extract_first(result, "手机号")
        parsed["id_card"] = _extract_first(result, "身份证号")
        parsed["email"] = _extract_first(result, "邮箱")
        parsed["education"] = _extract_first(result, "学历")
        parsed["school"] = _extract_first(result, "毕业院校")
        parsed["major"] = _extract_first(result, "专业")
        parsed["graduation_year"] = _parse_year(_extract_first(result, "毕业年份"))

        # 工作经历
        companies = _extract_all(result, "公司")
        positions = _extract_all(result, "职位")
        work_times = _extract_all(result, "工作时间")
        work_exp = []
        for i, company in enumerate(companies):
            exp = {
                "company": company,
                "position": positions[i] if i < len(positions) else "",
                "period": work_times[i] if i < len(work_times) else "",
            }
            work_exp.append(exp)
        parsed["work_experience"] = work_exp

        # 技能
        skills_raw = _extract_all(result, "技能")
        parsed["skills"] = skills_raw

    return parsed


def _extract_first(result: dict, key: str) -> str:
    """从 UIE 结果中提取指定 schema 的第一个值。"""
    items = result.get(key, [])
    if items and len(items) > 0:
        return items[0].get("text", "")
    return ""


def _extract_all(result: dict, key: str) -> list[str]:
    """从 UIE 结果中提取指定 schema 的所有值。"""
    items = result.get(key, [])
    return [item.get("text", "") for item in items]


def _parse_year(text: str) -> int | None:
    """尝试从文本中解析年份。"""
    if not text:
        return None
    import re
    match = re.search(r"(\d{4})", text)
    if match:
        return int(match.group(1))
    return None


# ---------- 第二阶段：qwen-plus 校验修正 ----------

VALIDATE_PROMPT = """你是一个简历信息校验专家。请根据以下简历原文，检查AI提取的结构化字段是否正确。

## 简历原文
{text}

## AI提取结果
{extracted}

## 要求
1. 逐一检查每个字段是否与原文一致
2. 如有错误，修正为正确值
3. 如有遗漏的重要信息，补充完整
4. 工作经历中每段应包含：company、position、period、description
5. 直接输出修正后的完整JSON，不要输出其他内容

## 输出格式（严格JSON）
{{
  "name": "",
  "phone": "",
  "id_card": "",
  "email": "",
  "education": "",
  "school": "",
  "major": "",
  "graduation_year": null,
  "work_experience": [
    {{"company": "", "position": "", "period": "", "description": ""}}
  ],
  "skills": []
}}
"""


def validate_with_qwen(text: str, uie_result: dict) -> dict:
    """第二阶段：使用 qwen-plus 校验和修正 UIE 提取结果。"""
    prompt = VALIDATE_PROMPT.format(
        text=text,
        extracted=json.dumps(uie_result, ensure_ascii=False, indent=2),
    )

    resp = Generation.call(
        model=settings.LLM_VALIDATE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        temperature=0.1,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"qwen-plus 调用失败: {resp.code} {resp.message}")

    content = resp.output.choices[0].message.content.strip()
    # 提取 JSON（可能被 ```json ... ``` 包裹）
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content)


# ---------- 两阶段统一入口 ----------

def extract_resume_fields(text: str) -> dict:
    """两阶段提取：UIE 初筛 + qwen-plus 校验。"""
    # 第一阶段
    uie_result = extract_with_uie(text)
    # 第二阶段
    validated = validate_with_qwen(text, uie_result)
    return validated
