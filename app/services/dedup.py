import json
import os

import faiss
import numpy as np

from app.config import settings
from app.services.embedding import get_embedding, get_embeddings


class ResumeDedup:
    """基于 FAISS 的简历向量去重（本地文件存储）。"""

    def __init__(self):
        self.dim = settings.EMBEDDING_DIM
        self.db_dir = settings.FAISS_INDEX_DIR
        os.makedirs(self.db_dir, exist_ok=True)

        self.index_path = os.path.join(self.db_dir, "faiss.index")
        self.meta_path = os.path.join(self.db_dir, "meta.json")

        self.index = faiss.IndexFlatIP(self.dim)  # 内积 = 余弦（归一化后）
        self.metadata: list[dict] = []  # [{resume_id, text}, ...]

        self._load()

    def _load(self):
        """从磁盘加载已有索引。"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def _save(self):
        """持久化索引到磁盘。"""
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)

    @staticmethod
    def _normalize(vec: list[float]) -> np.ndarray:
        """L2 归一化向量，使内积等价于余弦相似度。"""
        arr = np.array(vec, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def add_resume(self, resume_id: int, text: str) -> str:
        """将简历向量化并存入索引，返回向量 ID。"""
        vec = get_embedding(text)
        norm_vec = self._normalize(vec)
        self.index.add(norm_vec)
        vid = self.index.ntotal - 1
        self.metadata.append({"resume_id": resume_id, "text": text[:8192]})
        self._save()
        return str(vid)

    def add_batch(self, resume_ids: list[int], texts: list[str]):
        """批量添加简历向量。"""
        vecs = get_embeddings(texts)
        norm_vecs = np.array(
            [self._normalize(v).flatten() for v in vecs], dtype=np.float32
        )
        self.index.add(norm_vecs)
        for rid, text in zip(resume_ids, texts):
            self.metadata.append({"resume_id": rid, "text": text[:8192]})
        self._save()

    def check_duplicate(self, text: str) -> tuple[bool, int | None, float]:
        """检查是否存在相似简历。
        返回: (是否重复, 相似简历ID, 相似度分数)
        """
        if self.index.ntotal == 0:
            return False, None, 0.0

        vec = get_embedding(text)
        norm_vec = self._normalize(vec)
        scores, indices = self.index.search(norm_vec, 1)

        if indices[0][0] >= 0:
            idx = indices[0][0]
            score = float(scores[0][0])
            resume_id = self.metadata[idx]["resume_id"]
            if score >= settings.DEDUP_SIMILARITY_THRESHOLD:
                return True, resume_id, score
        return False, None, 0.0

    def search_similar(self, text: str, top_k: int = 20) -> list[dict]:
        """检索最相似的 top_k 个简历。"""
        if self.index.ntotal == 0:
            return []

        vec = get_embedding(text)
        norm_vec = self._normalize(vec)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(norm_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self.metadata[idx]
            results.append({
                "resume_id": meta["resume_id"],
                "score": float(score),
            })
        return results

    def delete_resume(self, resume_id: int):
        """标记删除（FAISS 不支持直接删除，这里仅从 metadata 标记）。"""
        for item in self.metadata:
            if item["resume_id"] == resume_id:
                item["resume_id"] = -1
        self._save()


# 全局单例
_dedup_instance = None


def get_dedup() -> ResumeDedup:
    global _dedup_instance
    if _dedup_instance is None:
        _dedup_instance = ResumeDedup()
    return _dedup_instance
