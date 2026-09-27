"""简历去重：稳定锚点向量的精确检索。

去重侧刻意不建近似索引。理由是阈值：0.95 卡得非常紧，而近似索引（IVF 的
簇剪枝、HNSW 的图剪枝）在紧阈值附近的漏召正是最容易被漏掉的那一批——漏掉
一个，就是一份重复简历进了库。这一侧用确定的延迟换确定的召回。

这里删掉的是一整套「标记 + 延迟回收」：不需要 vid 映射（向量的主键就是业务
表主键，重建索引不动数据行）、不需要删除集合、不需要检索多取公式、不需要
重建时的双缓冲原子切换。删除就是 DELETE，回收由 VACUUM / REINDEX 负责。
让一整类工程问题不需要存在，本身就是选型带来的收益。

判重不是自动删除：结果带上「疑似重复」标记和相似度分数，由 HR 确认。自动
丢弃在招人场景里是不可逆的数据损失。
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.models.resume import ResumeFields
from app.services.embedding import embed_text


def check_duplicate(
    db: Session,
    text: str,
    exclude_resume_id: int | None = None,
) -> tuple[bool, int | None, float]:
    """检查锚点特征文本是否与库内简历重复。

    返回: (是否重复, 相似简历ID, 相似度分数)

    exclude_resume_id 用于重新解析的场景——此时该简历的旧向量还在库里，
    不排除掉就会和自己比对出一个 1.0 的假重复。
    """
    if not text:
        return False, None, 0.0

    vec = embed_text(text)
    similarity = ResumeFields.dedup_vec.max_inner_product(vec)

    query = (
        db.query(ResumeFields.resume_id, similarity.label("neg_inner_product"))
        .filter(ResumeFields.is_duplicate.is_(False))
        .filter(ResumeFields.dedup_vec.isnot(None))
    )
    if exclude_resume_id is not None:
        query = query.filter(ResumeFields.resume_id != exclude_resume_id)

    # 精确检索下取 top-1 就够：结果按相似度降序排，第一条就是全库最大值，
    # 它不达标则全库不达标。近似索引下不能这么省——近似排序的第一名未必
    # 是真的第一名，所以才要多取几个候选。
    row = query.order_by(similarity).limit(1).first()
    if row is None:
        return False, None, 0.0

    score = -float(row.neg_inner_product)
    if score >= settings.DEDUP_SIMILARITY_THRESHOLD:
        return True, row.resume_id, score
    return False, None, 0.0
