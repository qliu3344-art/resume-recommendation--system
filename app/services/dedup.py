import os

from pymilvus import MilvusClient, DataType

from app.config import settings
from app.services.embedding import get_embedding


class ResumeDedup:
    """基于 Milvus Lite 的简历向量去重。"""

    def __init__(self):
        os.makedirs(os.path.dirname(settings.MILVUS_DB_PATH), exist_ok=True)
        self.client = MilvusClient(uri=settings.MILVUS_DB_PATH)
        self.collection_name = "resume_vectors"
        self._ensure_collection()

    def _ensure_collection(self):
        """确保集合存在，不存在则创建。"""
        if not self.client.has_collection(self.collection_name):
            schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field("id", DataType.INT64, is_primary=True)
            schema.add_field("resume_id", DataType.INT64)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM)
            schema.add_field("text", DataType.VARCHAR, max_length=8192)

            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="FLAT",
                metric_type="COSINE",
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params,
            )

    def add_resume(self, resume_id: int, text: str) -> str:
        """将简历向量化并存入 Milvus，返回向量 ID。"""
        vector = get_embedding(text)
        result = self.client.insert(
            collection_name=self.collection_name,
            data=[{
                "resume_id": resume_id,
                "vector": vector,
                "text": text[:8192],
            }],
        )
        return str(result["ids"][0])

    def check_duplicate(self, text: str) -> tuple[bool, int | None, float]:
        """检查是否存在相似简历。
        返回: (是否重复, 相似简历ID, 相似度分数)
        """
        vector = get_embedding(text)
        results = self.client.search(
            collection_name=self.collection_name,
            data=[vector],
            limit=1,
            output_fields=["resume_id"],
            search_params={"metric_type": "COSINE"},
        )
        if results and len(results[0]) > 0:
            top = results[0][0]
            score = top["distance"]
            resume_id = top["entity"]["resume_id"]
            if score >= settings.DEDUP_SIMILARITY_THRESHOLD:
                return True, resume_id, score
        return False, None, 0.0

    def delete_resume(self, resume_id: int):
        """删除指定简历的向量。"""
        self.client.delete(
            collection_name=self.collection_name,
            filter=f"resume_id == {resume_id}",
        )


# 全局单例
_dedup_instance = None


def get_dedup() -> ResumeDedup:
    global _dedup_instance
    if _dedup_instance is None:
        _dedup_instance = ResumeDedup()
    return _dedup_instance
