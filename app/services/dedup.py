import json
import os

import faiss
import numpy as np

from app.config import settings
from app.services.embedding import get_embedding, get_embeddings


class ResumeDedup:
    """基于 FAISS 的简历向量去重（本地文件存储）。

    FAISS 不支持向量删除，因此采用"标记删除 + 搜索过滤"策略：
      - 每个向量分配唯一 vid（单调递增），metadata 字典按 vid 索引
      - 删除时只标记 deleted_vids 集合，不修改 FAISS 索引
      - 搜索时过滤掉已删除 vid 的结果
      - 定期调用 compact() 可重建索引，物理清除已删除向量
    """

    def __init__(self):
        self.dim = settings.EMBEDDING_DIM
        self.db_dir = settings.FAISS_INDEX_DIR
        os.makedirs(self.db_dir, exist_ok=True)

        self.index_path = os.path.join(self.db_dir, "faiss.index")
        self.meta_path = os.path.join(self.db_dir, "meta.json")
        self.deleted_path = os.path.join(self.db_dir, "deleted.json")

        self.index = faiss.IndexFlatIP(self.dim)  # 内积 = 余弦（归一化后）
        self.metadata: dict[int, dict] = {}        # {vid: {resume_id, text}}
        self.deleted_vids: set[int] = set()        # 已标记删除的 vid 集合
        self._next_vid: int = 0                    # 下一个可用 vid

        self._load()

    def _load(self):
        """从磁盘加载已有索引和元数据。"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # 兼容旧格式（list）和新格式（dict）
                if isinstance(raw, list):
                    self.metadata = {i: item for i, item in enumerate(raw)}
                else:
                    self.metadata = {int(k): v for k, v in raw.items()}
        if os.path.exists(self.deleted_path):
            with open(self.deleted_path, "r", encoding="utf-8") as f:
                self.deleted_vids = set(json.load(f))
        # 计算下一个 vid
        if self.metadata:
            self._next_vid = max(self.metadata.keys()) + 1
        else:
            self._next_vid = self.index.ntotal

    def _save(self):
        """持久化索引和元数据到磁盘。"""
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)
        with open(self.deleted_path, "w", encoding="utf-8") as f:
            json.dump(list(self.deleted_vids), f, ensure_ascii=False)

    def _map_faiss_to_vid(self, faiss_pos: int) -> int | None:
        """将 FAISS 内部位置映射回 vid。

        FAISS 索引中的位置 = 向量添加顺序。由于我们不从 FAISS 中删除向量，
        FAISS 位置 == vid（因为 vid 也是单调递增的添加顺序）。
        但 compact() 重建后这个关系可能改变，因此 metadata 用 vid（而非 FAISS 位置）索引。
        """
        # 当前实现中 vid == FAISS 位置，因为从未真正删除 FAISS 向量
        return faiss_pos

    @staticmethod
    def _normalize(vec: list[float]) -> np.ndarray:
        """L2 归一化向量，使内积等价于余弦相似度。"""
        arr = np.array(vec, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def add_resume(self, resume_id: int, text: str) -> str:
        """将简历向量化并存入索引，返回稳定 vid。"""
        vec = get_embedding(text)
        norm_vec = self._normalize(vec)
        self.index.add(norm_vec)
        vid = self._next_vid
        self._next_vid += 1
        self.metadata[vid] = {"resume_id": resume_id, "text": text[:8192]}
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
            vid = self._next_vid
            self._next_vid += 1
            self.metadata[vid] = {"resume_id": rid, "text": text[:8192]}
        self._save()

    def check_duplicate(self, text: str) -> tuple[bool, int | None, float]:
        """检查是否存在相似简历（跳过已删除记录）。

        返回: (是否重复, 相似简历ID, 相似度分数)
        """
        if self.index.ntotal == 0:
            return False, None, 0.0

        vec = get_embedding(text)
        norm_vec = self._normalize(vec)

        # 搜索 top-k（可能前面几个都是已删除的）
        search_k = min(10, self.index.ntotal)
        scores, indices = self.index.search(norm_vec, search_k)

        for i in range(search_k):
            faiss_pos = int(indices[0][i])
            if faiss_pos < 0:
                continue
            vid = self._map_faiss_to_vid(faiss_pos)
            if vid in self.deleted_vids:
                continue
            if vid not in self.metadata:
                continue
            score = float(scores[0][i])
            if score >= settings.DEDUP_SIMILARITY_THRESHOLD:
                resume_id = self.metadata[vid]["resume_id"]
                return True, resume_id, score

        return False, None, 0.0

    def search_similar(self, text: str, top_k: int = 20) -> list[dict]:
        """检索最相似的 top_k 个简历（跳过已删除记录）。"""
        if self.index.ntotal == 0:
            return []

        vec = get_embedding(text)
        norm_vec = self._normalize(vec)

        # 多取一些候选，过滤已删除后仍有足够结果
        fetch_k = min(top_k * 2 + len(self.deleted_vids), self.index.ntotal)
        scores, indices = self.index.search(norm_vec, fetch_k)

        results = []
        for score, faiss_pos in zip(scores[0], indices[0]):
            if faiss_pos < 0:
                continue
            vid = self._map_faiss_to_vid(int(faiss_pos))
            if vid in self.deleted_vids:
                continue
            if vid not in self.metadata:
                continue
            meta = self.metadata[vid]
            results.append({
                "resume_id": meta["resume_id"],
                "score": float(score),
            })
            if len(results) >= top_k:
                break

        return results

    def delete_resume(self, resume_id: int):
        """标记删除简历（不修改 FAISS 索引，搜索时自动过滤）。"""
        for vid, meta in self.metadata.items():
            if meta["resume_id"] == resume_id:
                self.deleted_vids.add(vid)
        self._save()

    def compact(self):
        """重建 FAISS 索引，物理清除已删除向量。

        调用时机：累积删除较多时（如 deleted_vids > 100），或定期维护。
        """
        if not self.deleted_vids:
            return

        active = [
            (vid, meta)
            for vid, meta in self.metadata.items()
            if vid not in self.deleted_vids
        ]
        if not active:
            # 全部删了，重建空索引
            self.index = faiss.IndexFlatIP(self.dim)
            self.metadata = {}
            self.deleted_vids = set()
            self._next_vid = 0
            self._save()
            return

        # 重新分配 vid：保持单调递增
        old_to_new: dict[int, int] = {}
        new_metadata: dict[int, dict] = {}
        new_index = faiss.IndexFlatIP(self.dim)

        # 需要重新向量化每条记录
        texts = [meta["text"] for _, meta in active]
        vecs = get_embeddings(texts)
        norm_vecs = np.array(
            [self._normalize(v).flatten() for v in vecs], dtype=np.float32
        )
        new_index.add(norm_vecs)

        for new_vid, (old_vid, meta) in enumerate(active):
            new_metadata[new_vid] = meta
            old_to_new[old_vid] = new_vid

        self.index = new_index
        self.metadata = new_metadata
        self.deleted_vids = set()
        self._next_vid = len(new_metadata)
        self._save()


# 全局单例
_dedup_instance = None


def get_dedup() -> ResumeDedup:
    global _dedup_instance
    if _dedup_instance is None:
        _dedup_instance = ResumeDedup()
    return _dedup_instance
