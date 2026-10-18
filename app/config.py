import os
from pathlib import Path
from urllib.parse import quote_plus

# paddlepaddle 2.6.2 与新版 protobuf 无法共存：paddle 要求 protobuf<=3.20.2，
# 而环境里 googleapis-common-protos / opentelemetry-proto 要求 >=4.25.8，
# 两个区间不相交，装哪个都会让另一边报 "Descriptors cannot be created directly"。
# 官方给的逃生口是让 protobuf 走纯 Python 解析实现，绕过 C++ 描述符那条路径。
# 只在导入 paddle 前需要生效，开销在模型加载期，不在请求热路径上。
# 必须在 paddle 被导入之前设置——paddle 的 Taskflow 是在函数内惰性导入的，
# 但那时本模块早已加载完毕。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# 加载 .env 文件
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class Settings:
    PROJECT_NAME: str = "智能简历推荐系统"
    VERSION: str = "2.0.0"

    # PostgreSQL + pgvector：向量和业务数据同库同事务
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_USER: str = os.getenv("PG_USER", "postgres")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "")
    PG_DB: str = os.getenv("PG_DB", "resume_system")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.PG_USER}:{quote_plus(self.PG_PASSWORD)}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        )

    # DashScope (阿里云百炼)
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")

    # 模型配置
    LLM_VALIDATE_MODEL: str = "qwen-plus"
    LLM_JUDGE_MODEL: str = "qwen3-max"  # judge 与生成分开用档，避免同一模型自评偏差
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_DIM: int = 1024

    # 文件存储
    UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "resumes"
    )

    # 去重阈值：刻意取高。假阳性是不可逆的数据丢失，假阴性可恢复，
    # 两类错误代价不对称，所以往高取
    DEDUP_SIMILARITY_THRESHOLD: float = 0.95

    # 匹配权重：网格搜索在 [0.3, 0.7] 按 0.05 步长扫 9 个点取峰值
    KEYWORD_MATCH_WEIGHT: float = 0.4
    SEMANTIC_MATCH_WEIGHT: float = 0.6

    # 语义检索封顶：返回更多没有业务意义，而且会掩盖上游门槛配置问题
    SEMANTIC_SEARCH_MAX_K: int = 200

    # 岗位描述短于这个长度就算「质量不足」，先用 LLM 结构化成与简历侧同一套
    # 字段形态再向量化
    JOB_DESCRIPTION_MIN_LEN: int = 30

    # HNSW 运行时参数。迭代扫描用于防 overfiltering：索引默认先取 ef_search
    # 个候选再拿 WHERE 去筛，过滤选择性一低就返回不足，开了之后继续扫直到凑够
    # 或撞上 max_scan_tuples。需要 pgvector 0.8.0+
    HNSW_EF_SEARCH: int = 100
    HNSW_ITERATIVE_SCAN: str = "relaxed_order"
    HNSW_MAX_SCAN_TUPLES: int = 20000


settings = Settings()
