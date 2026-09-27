"""初始化数据库：建库 + 建扩展 + 建表 + 建索引。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import psycopg
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base
from app.models import resume, job  # noqa: F401 确保模型注册


def create_database():
    """创建数据库（如果不存在）。"""
    conn = psycopg.connect(
        host=settings.PG_HOST,
        port=settings.PG_PORT,
        user=settings.PG_USER,
        password=settings.PG_PASSWORD,
        dbname="postgres",
        autocommit=True,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (settings.PG_DB,)
            )
            if cursor.fetchone():
                print(f"✅ 数据库 `{settings.PG_DB}` 已存在")
            else:
                cursor.execute(f'CREATE DATABASE "{settings.PG_DB}"')
                print(f"✅ 数据库 `{settings.PG_DB}` 已创建")
    finally:
        conn.close()


def create_extension():
    """启用 pgvector 扩展，并报告版本。"""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        version = conn.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
    print(f"✅ 扩展 vector 已就绪（版本 {version}）")


def create_tables():
    """创建所有表。"""
    Base.metadata.create_all(bind=engine)
    print("✅ 所有表已创建")


def create_indexes():
    """建索引。去重和检索两侧的策略是分开定的，索引也分开。"""
    with engine.begin() as conn:
        # 门槛项：B-tree。让「学历达标 且 年限达标」这一步在数据库层用索引
        # 先粗筛，把候选集从几千降到几百，而不是把全表拉进应用层逐条判断
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_resume_fields_gates "
            "ON resume_fields (education_level, work_months)"
        ))
        # 检索侧：HNSW。检索的输出是 top-K 排序而不是二值判定，不存在去重
        # 侧那条很紧的线，近似的召回损失换来的是延迟上的余量，这笔交换成立。
        # 用的是内积算子（vector_ip_ops），对应 L2 归一化后的 <#>
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_resume_fields_retrieval_hnsw "
            "ON resume_fields USING hnsw (retrieval_vec vector_ip_ops)"
        ))
        # 去重侧刻意不建索引：0.95 的阈值很紧，近似索引在紧阈值附近的漏召
        # 是不可逆的数据丢失，这一侧用确定的延迟换确定的召回
    print("✅ 索引已创建（检索侧 HNSW；去重侧走精确检索，不建索引）")


if __name__ == "__main__":
    create_database()
    create_extension()
    create_tables()
    create_indexes()
    print("🎉 数据库初始化完成")
