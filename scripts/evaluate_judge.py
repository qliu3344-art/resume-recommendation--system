"""LLM-as-judge 评估：用 qwen 评匹配质量。

弥补 evaluate.py 里 evaluate_matching 只看分数分布的不足——分数分布合理
不代表每个匹配真的相关（关键词堆砌也能拿高分）。这里用 LLM 当 judge，
对匹配结果做语义级判断，得到「真正相关」的比例。

用法：python scripts/evaluate_judge.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import dashscope
from dashscope import Generation

from app.config import settings
from app.database import SessionLocal
from app.models.job import Job, JobMatch
from app.models.resume import ResumeFields
from app.services.ai_extractor import _parse_json_response

dashscope.api_key = settings.DASHSCOPE_API_KEY

JUDGE_PROMPT = """你是招聘匹配质量评估专家。判断这位候选人是否「真正适合」岗位，而不是只看关键词有没有对上。

## 岗位描述
{job_desc}

## 候选人结构化字段
{resume_fields}

## 匹配引擎打分
关键词分 {keyword_score} / 语义分 {semantic_score} / 综合分 {total_score}

## 判断标准
- 真正相关 = 工作内容/技术栈/方向确实匹配，学历年限达标
- 不相关 = 仅关键词命中但方向偏离（如「Java 培训讲师」匹配「Java 开发」）
- 不看匹配引擎给的分数，独立判断

## 输出（严格 JSON，不要输出其他内容）
{{"relevant": true, "reason": "一句话理由"}}
"""


def judge_relevance(job_desc, resume_fields, keyword_score, semantic_score, total_score) -> dict:
    """调用 qwen 判断一个匹配是否真正相关，返回 {"relevant": bool|None, "reason": str}。"""
    prompt = JUDGE_PROMPT.format(
        job_desc=job_desc,
        resume_fields=json.dumps(resume_fields, ensure_ascii=False, indent=2),
        keyword_score=keyword_score,
        semantic_score=semantic_score,
        total_score=total_score,
    )
    resp = Generation.call(
        model=settings.LLM_VALIDATE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        temperature=0.1,  # judge 要确定性
    )
    if resp.status_code != 200:
        return {"relevant": None, "reason": f"judge 调用失败: {resp.code} {resp.message}"}
    content = resp.output.choices[0].message.content
    return _parse_json_response(content)


def evaluate_matching_quality(db, sample_size: int = 20):
    """对匹配结果做 LLM-as-judge 语义评估，统计「真正相关」比例。"""
    matches = (
        db.query(JobMatch)
        .order_by(JobMatch.total_score.desc())
        .limit(sample_size)
        .all()
    )
    if not matches:
        print("⚠️ 没有匹配数据，请先运行匹配流程")
        return

    judged_relevant = 0
    judged_total = 0
    print(f"📊 LLM-as-judge 匹配质量评估（评估前 {len(matches)} 个高匹配）:\n")

    for m in matches:
        job = db.query(Job).filter(Job.id == m.job_id).first()
        rf = db.query(ResumeFields).filter(ResumeFields.resume_id == m.resume_id).first()
        if not job or not rf:
            continue

        job_desc = job.description or job.title
        resume_fields = {
            "education": rf.education,
            "school": rf.school,
            "major": rf.major,
            "skills": rf.skills,
            "work_experience": rf.work_experience,
            "project_experience": rf.project_experience,
        }
        result = judge_relevance(
            job_desc, resume_fields,
            m.keyword_score, m.semantic_score, m.total_score,
        )
        judged_total += 1
        relevant = result.get("relevant")
        if relevant is True:
            judged_relevant += 1
        print(
            f"  resume {m.resume_id}: total {m.total_score:.3f} "
            f"-> judge {'相关' if relevant is True else ('不相关' if relevant is False else '未知')} "
            f"| {result.get('reason', '')}"
        )

    if judged_total == 0:
        print("\n⚠️ 没有可评估的匹配（缺少关联的 job 或 resume）")
        return
    ratio = judged_relevant / judged_total
    print(f"\n📊 LLM-judge 真正相关率: {judged_relevant}/{judged_total} ({ratio:.1%})")
    print("对比：匹配引擎的总分分布（evaluate.py 的 evaluate_matching）只反映分数合理性，")
    print("这里 judge 的结果反映「语义上是否真匹配」，两者结合才是完整的匹配质量评估。")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        evaluate_matching_quality(db)
    finally:
        db.close()
