"""文本向量化。

L2 归一化封装在这一层，入库和查询都必须走这里——只归一化一边，内积就不再
是余弦而是一个缩放过的内积，所有阈值会一起失效。做法是把归一化放在两条路
的公共入口上，避免将来有一条路漏掉（讲稿 P082）。
"""
import math

import dashscope
from dashscope import TextEmbedding

from app.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY

# DashScope 批量接口单次上限
_BATCH_SIZE = 6


def l2_normalize(vec: list[float]) -> list[float]:
    """L2 归一化，使内积等价于余弦相似度。

    文本向量的模长受文本长度影响——长简历的向量模长天然更大。欧氏距离会
    把「长」当成「远」，余弦只看方向。归一化之后内积就是余弦，而内积是
    向量索引里更快的算子（pgvector 里是 <#>，取负内积距离）。
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


def embed_text(text: str) -> list[float]:
    """文本 → 已归一化向量。入库和查询共用这一个入口。"""
    resp = TextEmbedding.call(
        model=settings.EMBEDDING_MODEL,
        input=text,
        dimension=settings.EMBEDDING_DIM,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding 调用失败: {resp.code} {resp.message}")
    return l2_normalize(resp.output["embeddings"][0]["embedding"])


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量文本 → 已归一化向量。"""
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = TextEmbedding.call(
            model=settings.EMBEDDING_MODEL,
            input=batch,
            dimension=settings.EMBEDDING_DIM,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding 批量调用失败: {resp.code} {resp.message}")
        all_embeddings.extend(
            l2_normalize(item["embedding"]) for item in resp.output["embeddings"]
        )
    return all_embeddings
