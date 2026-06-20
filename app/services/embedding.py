import dashscope
from dashscope import TextEmbedding

from app.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY


def get_embedding(text: str) -> list[float]:
    """将文本转换为向量，使用 text-embedding-v3。"""
    resp = TextEmbedding.call(
        model=settings.EMBEDDING_MODEL,
        input=text,
        dimension=settings.EMBEDDING_DIM,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Embedding 调用失败: {resp.code} {resp.message}")
    return resp.output["embeddings"][0]["embedding"]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量将文本转换为向量（每次最多 25 条）。"""
    all_embeddings = []
    batch_size = 25
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = TextEmbedding.call(
            model=settings.EMBEDDING_MODEL,
            input=batch,
            dimension=settings.EMBEDDING_DIM,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding 批量调用失败: {resp.code} {resp.message}")
        batch_result = [item["embedding"] for item in resp.output["embeddings"]]
        all_embeddings.extend(batch_result)
    return all_embeddings
