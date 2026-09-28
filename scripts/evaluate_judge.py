"""LLM-as-judge 评估：用独立评审模型判定匹配是否真正相关。

离线指标（分数分布）测不出相关性——分数高不等于匹配，关键词堆砌就能拿
高分。所以引入 LLM 做语义级的独立判断。

核心设计只有一条：必须切断 judge 与被评对象的耦合。prompt 里给了引擎打分，
但明确要求「不要看分数，独立判断」。如果不断开，judge 会锚定在给它的分数
上——你给它 0.95，它大概率说相关，judge 就退化成了对引擎的复述，失去校验
意义。这是 judge 设计里最容易做错、也最致命的一点。

三个已知偏差，逐个处理：
  · 锚定偏差 —— prompt 显式声明不看分数
  · 长度偏差 —— 判据里声明「只看方向是否匹配，不看信息量」
  · 样本选择偏差 —— 两端都要抽。只抽高分段看到的都是「看起来相关」的，
    是系统性高估，不是系统好

校准口径：抽 100 条人工标注样本与 judge 结果做一致性比对，一致率过 80%
才敢把 judge 的分数当指标用；没过只能当参考，不能进任何加权公式。

⚠️ 口径分界（重要）：本脚本跑在 generate_mock_data.py 造的合成数据上时，
   得到的是一个**很低的数**，而且那是对的——合成数据的技能是随机分配的，
   候选人之间本来就没有真实的语义对齐，judge 判「不相关」是准确判断。
   所以这个数**不能当作匹配质量的指标**，它只说明 judge 在按语义判、
   没有被引擎给的分数锚定住。对外报的相关率来自真实简历与真实岗位的评估集。

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

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CALIBRATION_PATH = os.path.join(BASE_DIR, "data", "labels", "judge_calibration.json")

# judge 校准门槛：低于它 judge 分数不得进任何加权公式（口径与项目一一致）
CALIBRATION_MIN_AGREEMENT = 0.80

JUDGE_PROMPT = """你是招聘匹配质量评估专家。判断这位候选人是否「真正适合」岗位，而不是只看关键词有没有对上。

## 岗位描述
{job_desc}

## 候选人结构化字段
{resume_fields}

## 匹配引擎打分
关键词分 {keyword_score} / 语义分 {semantic_score} / 综合分 {total_score}

## 判断标准
- 真正相关 = 工作内容 / 技术栈 / 方向确实匹配
- 不相关 = 仅关键词命中但方向偏离（如「Java 培训讲师」匹配「Java 开发岗」）
- 只看方向是否匹配，不看信息量——信息全但方向不对，判不相关
- 不要看匹配引擎给的分数，独立判断

## 输出（严格 JSON，不要输出其他内容）
{{"relevant": true, "reason": "一句话理由"}}
"""


def judge_relevance(job_desc, resume_fields, keyword_score, semantic_score, total_score) -> dict:
    """调用 judge 模型判断一个匹配是否真正相关。"""
    prompt = JUDGE_PROMPT.format(
        job_desc=job_desc,
        resume_fields=json.dumps(resume_fields, ensure_ascii=False, indent=2),
        keyword_score=keyword_score,
        semantic_score=semantic_score,
        total_score=total_score,
    )
    # judge 另起一档，用更高一档的模型——判分和生成不是同一件事
    resp = Generation.call(
        model=settings.LLM_JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        temperature=0,  # judge 要确定性，与校验阶段同一条规矩
    )
    if resp.status_code != 200:
        return {"relevant": None, "reason": f"judge 调用失败: {resp.code} {resp.message}"}
    return _parse_json_response(resp.output.choices[0].message.content)


def load_calibration_agreement() -> float | None:
    """读 judge 校准一致率。

    标注文件形如 [{"human_relevant": true, "judge_relevant": true}, ...]，
    覆盖判相关和判不相关两边。文件不存在就返回 None——没有校准过的 judge
    不能当指标用。
    """
    if not os.path.exists(CALIBRATION_PATH):
        return None
    with open(CALIBRATION_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)
    if not samples:
        return None
    agreed = sum(
        1 for s in samples if bool(s.get("human_relevant")) == bool(s.get("judge_relevant"))
    )
    return agreed / len(samples)


def _resume_payload(rf: ResumeFields) -> dict:
    return {
        "education": rf.education,
        "school": rf.school,
        "major": rf.major,
        "skills": rf.skills,
        "work_experience": rf.work_experience,
        "project_experience": rf.project_experience,
    }


def evaluate_matching_quality(db, job_limit: int = 50, per_job_k: int = 20):
    """按「岗位 × top-K」评估真正相关率。

    口径要带 K：K 越大相关率必然越低，top-5 里几乎都是强相关的，top-50 里
    混进弱相关的概率就高了。脱离 K 报一个「匹配准确率 92%」，被问一句
    「那 top-50 呢」就答不上来了。

    抽样必须覆盖两端：送评的是每岗 top-K 的全部，而不是只抽前几名。
    """
    jobs = db.query(Job).limit(job_limit).all()
    if not jobs:
        print("⚠️ 没有岗位数据，请先运行匹配流程")
        return None

    judged_relevant = 0
    judged_total = 0

    for job in jobs:
        matches = (
            db.query(JobMatch)
            .filter(JobMatch.job_id == job.id)
            .order_by(JobMatch.total_score.desc())
            .limit(per_job_k)
            .all()
        )
        for m in matches:
            rf = db.query(ResumeFields).filter(ResumeFields.resume_id == m.resume_id).first()
            if rf is None:
                continue
            result = judge_relevance(
                job.description or job.title,
                _resume_payload(rf),
                m.keyword_score, m.semantic_score, m.total_score,
            )
            if result.get("relevant") is None:
                continue
            judged_total += 1
            if result["relevant"] is True:
                judged_relevant += 1

    if judged_total == 0:
        print("⚠️ 没有可评估的匹配")
        return None

    ratio = judged_relevant / judged_total
    print(f"\n📊 LLM-as-judge 真正相关率（{len(jobs)} 岗 × top-{per_job_k}）:")
    print(f"   {judged_relevant}/{judged_total} = {ratio:.1%}")
    print(f"   ⚠️ 报这个数必须带 K：它是 top-{per_job_k} 口径，K 变大相关率会下降。")
    print("   ⚠️ 若跑的是合成数据，这个数会很低而且那是对的——合成数据的技能是")
    print("      随机分配的，候选人之间本就没有真实语义对齐。它只说明 judge 在")
    print("      按语义判、没被引擎分数锚定，不能当匹配质量指标用。")
    return ratio


def gate_on_calibration() -> bool:
    """judge 校准门槛检查。一致率没过 80%，判定结果只能当参考。"""
    agreement = load_calibration_agreement()
    if agreement is None:
        print(f"\n⚠️ 未找到 judge 校准标注文件（{CALIBRATION_PATH}）")
        print("   没有校准过的 judge，其判定只能当参考，不能进任何加权公式。")
        return False

    print(f"\n📊 judge 校准一致率: {agreement:.1%}")
    if agreement < CALIBRATION_MIN_AGREEMENT:
        print(f"   ❌ 低于 {CALIBRATION_MIN_AGREEMENT:.0%} 门槛——judge 分数不得进任何加权公式。")
        print("      一致率的参照系是人工标注者之间的一致率（通常在 0.8 上下），")
        print("      低于它说明 judge 比一个普通标注员还不可靠。")
        return False

    print(f"   ✅ 过 {CALIBRATION_MIN_AGREEMENT:.0%} 门槛，judge 分数可以作为指标使用。")
    print("      注意一致率跟着评估集走，换一批岗位或行业必须重测。")
    return True


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ratio = evaluate_matching_quality(db)
        passed = gate_on_calibration()
        if ratio is not None and not passed:
            print("\n⚠️ judge 未通过校准门槛，上面这个相关率只能当参考信号。")
    finally:
        db.close()
