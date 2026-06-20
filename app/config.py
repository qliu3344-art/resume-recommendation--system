import os
from pathlib import Path

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
    VERSION: str = "1.0.0"

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB: str = "resume_system"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    # DashScope (阿里云百炼)
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")

    # 模型配置
    LLM_VALIDATE_MODEL: str = "qwen-plus"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_DIM: int = 1024

    # FAISS 向量索引（纯英文路径，FAISS 不支持中文路径）
    FAISS_INDEX_DIR: str = "D:/GitHub/resume_system_data"

    # 文件存储
    UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "resumes"
    )

    # 匹配阈值
    DEDUP_SIMILARITY_THRESHOLD: float = 0.95
    KEYWORD_MATCH_WEIGHT: float = 0.4
    SEMANTIC_MATCH_WEIGHT: float = 0.6


settings = Settings()
