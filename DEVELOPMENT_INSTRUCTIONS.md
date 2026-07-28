# 智能简历推荐系统 — 开发指令

> **项目周期：** 2025.03 - 2025.10  
> **技术栈：** Python、FastAPI、MySQL、PaddleNLP、Milvus/FAISS、LangChain、RAG  
> **当前状态：** 核心功能已完成 ~70%，需补充测试、日志、部署配置、Milvus 迁移

---

## 一、项目业务全景

### 1.1 业务流程

```
HR 上传简历(PDF/Word) → 文件解析为文本
  → 阶段一：PaddleNLP UIE 小模型快速提取 20+ 字段
  → 阶段二：大模型(qwen-plus)校验修正提取结果
  → 去重检查（FAISS 向量相似度对比）
  → 敏感字段脱敏（手机号、身份证号、邮箱）
  → 存入 MySQL + 向量索引库
  → HR 设置岗位要求 → 双层匹配（关键词 + RAG 语义）→ 推荐排序 → HR 查看
```

### 1.2 核心模块

| 模块 | 功能 | 技术方案 |
|---|---|---|
| 简历文档管理 | 上传、解析、结构化提取 | FastAPI + PaddleNLP UIE + 通义千问 |
| 简历去重与脱敏 | 语义去重、隐私字段脱敏 | FAISS 向量检索 + 正则脱敏 |
| 人岗智能匹配 | 关键词硬匹配 + RAG 语义检索 | 双层评分架构 |

---

## 二、已完成功能（现有代码清单）

### 2.1 项目结构 ✅

```
简历推荐系统/
├── app/
│   ├── main.py              ✅ FastAPI 入口，注册 3 个路由
│   ├── config.py            ✅ Settings 类，.env 加载
│   ├── database.py          ✅ SQLAlchemy engine + Session
│   ├── models/
│   │   ├── resume.py        ✅ Resume 表 + ResumeFields 表
│   │   └── job.py           ✅ Job 表 + JobMatch 表
│   ├── schemas/
│   │   ├── resume.py        ✅ Pydantic 请求/响应模型
│   │   └── job.py           ✅ Pydantic 请求/响应模型
│   ├── services/
│   │   ├── parser.py        ✅ PDF(PyMuPDF) + DOCX(python-docx)
│   │   ├── ai_extractor.py  ✅ PaddleNLP UIE + qwen-plus 两阶段
│   │   ├── embedding.py     ✅ DashScope text-embedding-v3
│   │   ├── dedup.py         ✅ FAISS 向量去重(持久化)
│   │   ├── desensitize.py   ✅ 手机号/身份证/邮箱脱敏
│   │   └── matcher.py       ✅ 关键词匹配 + 语义检索双层
│   └── routers/
│       ├── resume.py        ✅ 上传/列表/详情/解析/脱敏
│       ├── job.py           ✅ 岗位 CRUD
│       └── match.py         ✅ 匹配/查看结果
├── scripts/
│   ├── init_db.py           ✅ 建库建表
│   ├── generate_mock_data.py✅ 500份简历 + 30岗位
│   ├── batch_import.py      ✅ 批量导入数据库 + 向量化
│   └── evaluate.py          ✅ 准确率/去重/匹配评估
├── data/
│   ├── resumes/             ✅ 简历文件存储
│   └── labels/              ✅ 标注数据
├── requirements.txt         ✅ 依赖清单
├── README.md                ✅ 项目文档
└── .env                     ✅ 环境变量
```

### 2.2 已验证可工作的链路

1. **上传 → 解析 → 提取 → 去重 → 入库**：完整闭环
2. **岗位 CRUD + 匹配推荐**：完整闭环
3. **脱敏查询**：可对已解析简历查询脱敏数据
4. **500 份模拟数据生成 + 批量导入**：可用
5. **评估脚本**：基础评估框架可用

---

## 三、待完成工作清单

### 3.1 高优先级（必须完成）

#### A. 测试体系 — `tests/` 目录

```
tests/
├── conftest.py              # pytest fixtures（测试DB、测试客户端）
├── test_parser.py           # PDF/DOCX 解析单测
├── test_ai_extractor.py     # UIE 提取 + qwen 校验单测
├── test_desensitize.py      # 脱敏函数单测
├── test_dedup.py            # 去重逻辑单测
├── test_matcher.py          # 关键词匹配 + 语义匹配单测
├── test_routers_resume.py   # 简历接口集成测试
├── test_routers_job.py      # 岗位接口集成测试
└── test_routers_match.py    # 匹配接口集成测试
```

**编写要求：**
- 使用 `pytest` + `httpx.AsyncClient`（FastAPI TestClient）
- 测试数据库使用 SQLite 内存模式，不走真实 MySQL
- FAISS/Embedding 调用需 Mock，不依赖外部 API
- 覆盖率目标：services 层 ≥ 90%，routers 层 ≥ 80%

**conftest.py 参考结构：**
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
```

#### B. 日志系统 — 新增 `app/logger.py`

```python
import logging
import sys

def setup_logger(name: str = "resume_system") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    ))
    logger.addHandler(console)
    
    # 文件 handler（按天轮转）
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        "logs/resume_system.log", when="midnight", backupCount=30, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    ))
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()
```

**要求：** 所有 services 和 routers 中的 `print()` 替换为 `logger.info()` / `logger.error()`。

#### C. 全局异常处理 — 新增 `app/exceptions.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code

class ParseException(AppException):
    def __init__(self, message: str):
        super().__init__(message, code=400)

class ExtractorException(AppException):
    def __init__(self, message: str):
        super().__init__(message, code=500)

class DuplicateException(AppException):
    def __init__(self, message: str, duplicate_id: int = None):
        self.duplicate_id = duplicate_id
        super().__init__(message, code=409)
```

然后在 `app/main.py` 注册：
```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.code, content={"detail": exc.message})
```

#### D. API 响应标准化

所有接口响应统一为：
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

需要新增 `app/schemas/common.py`：
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
```

#### E. 中间件 — 请求耗时日志

在 `app/main.py` 添加：
```python
import time
from fastapi import Request

@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.3f}s)")
    return response
```

### 3.2 中优先级（提升可靠性和可维护性）

#### F. 工作年限计算修正

当前 `matcher.py` 用工作经历段数当年限，不准确。需改为从 `work_experience[].period` 解析实际年限：

```python
def calc_work_years(work_experience: list) -> int:
    """从工作经历 period 字段计算实际工作年限。"""
    if not work_experience:
        return 0
    import re
    years_set = set()
    for exp in work_experience:
        period = exp.get("period", "")
        years = re.findall(r"(\d{4})", period)
        if years:
            start = int(years[0])
            end = int(years[-1]) if len(years) > 1 else 2025
            for y in range(start, end + 1):
                years_set.add(y)
    return len(years_set)
```

#### G. 简历上传重名处理

当前 `routers/resume.py` 直接用原始文件名存储，存在覆盖风险。改为：

```python
import uuid

file_stem, file_ext = os.path.splitext(file.filename)
safe_name = f"{file_stem}_{uuid.uuid4().hex[:8]}{file_ext}"
file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
```

#### H. 分页参数标准化

`list_resumes` 和 `list_jobs` 未返回分页元信息。改为：

```python
class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: list[T]
```

#### I. 配置文件分离

将 `config.py` 改为支持开发/生产环境：

```
app/
├── config.py              # 基类
├── config_dev.py          # 开发环境
└── config_prod.py         # 生产环境（从环境变量读取）
```

```python
# config.py
import os

class BaseConfig:
    PROJECT_NAME: str = "智能简历推荐系统"
    VERSION: str = "1.0.0"
    # ...

class DevConfig(BaseConfig):
    MYSQL_HOST: str = "localhost"
    DEBUG: bool = True

class ProdConfig(BaseConfig):
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "prod-mysql.internal")
    DEBUG: bool = False

def get_config():
    env = os.getenv("APP_ENV", "dev")
    return DevConfig() if env == "dev" else ProdConfig()
```

### 3.3 低优先级（锦上添花）

#### J. Docker 化部署

根目录新增：
```
Dockerfile
docker-compose.yml   # MySQL + App
```

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### K. 将 FAISS 迁移为 Milvus（可选）

当前用 FAISS + 磁盘持久化。若上线生产环境，建议迁移到 Milvus：
- 新建 `app/services/vector_store.py`，封装 `MilvusStore` 和 `FAISSStore` 统一接口
- `dedup.py` 依赖 `vector_store` 而非直接操作 FAISS
- 通过 config 切换：

```python
# 伪代码
class VectorStore(ABC):
    @abstractmethod
    def add(self, vectors, metadata): ...
    @abstractmethod
    def search(self, query_vector, top_k): ...

class FAISSStore(VectorStore): ...
class MilvusStore(VectorStore): ...
```

#### L. CI/CD — GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=app --cov-report=term
```

---

## 四、技术决策说明

| 决策点 | 选型 | 理由 |
|---|---|---|
| 小模型初筛 | PaddleNLP UIE-base | 本地运行免费用，信息抽取能力强，毫秒级响应 |
| 大模型校验 | 通义千问 qwen-plus | 性价比高，中文理解好，支持 JSON 结构化输出 |
| 向量数据库 | FAISS（当前）/ Milvus（生产） | FAISS 轻量免部署；Milvus 支持分布式、动态增删 |
| 文本向量化 | text-embedding-v3 (1024维) | DashScope 生态统一，1024 维度性价比好 |
| 脱敏方案 | 正则原地脱敏 | 简单可控，无需额外服务 |
| 匹配权重 | 关键词 0.4 + 语义 0.6 | 语义匹配为主，关键词保证硬性门槛 |

---

## 五、接口规范（完整 API 文档）

### 5.1 简历管理

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/api/v1/resumes/upload` | 上传简历文件(multipart) | ✅ |
| GET | `/api/v1/resumes` | 简历列表(分页) | ✅ |
| GET | `/api/v1/resumes/{id}` | 简历详情 | ✅ |
| POST | `/api/v1/resumes/{id}/parse` | 触发 AI 解析 | ✅ |
| GET | `/api/v1/resumes/{id}/desensitized` | 获取脱敏数据 | ✅ |
| DELETE | `/api/v1/resumes/{id}` | 删除简历 | ❌ 需新增 |

### 5.2 岗位管理

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/api/v1/jobs` | 创建岗位 | ✅ |
| GET | `/api/v1/jobs` | 岗位列表 | ✅ |
| GET | `/api/v1/jobs/{id}` | 岗位详情 | ✅ |
| PUT | `/api/v1/jobs/{id}` | 更新岗位 | ✅ |
| DELETE | `/api/v1/jobs/{id}` | 删除岗位 | ✅ |

### 5.3 智能匹配

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/api/v1/match/{job_id}?top_k=20` | 执行匹配 | ✅ |
| GET | `/api/v1/match/{job_id}/results` | 查看历史匹配 | ✅ |
| GET | `/api/v1/match/resume/{resume_id}` | 反查：某候选人匹配的岗位 | ❌ 需新增 |

### 5.4 新增接口

**DELETE `/api/v1/resumes/{id}`：**
```python
@router.delete("/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")
    
    # 删除关联字段
    db.query(ResumeFields).filter(ResumeFields.resume_id == resume_id).delete()
    # 删除关联匹配记录
    db.query(JobMatch).filter(JobMatch.resume_id == resume_id).delete()
    # 删除文件
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)
    # 标记向量库
    get_dedup().delete_resume(resume_id)
    # 删除记录
    db.delete(resume)
    db.commit()
    return {"message": "删除成功"}
```

**GET `/api/v1/match/resume/{resume_id}`：**
```python
@router.get("/resume/{resume_id}")
def match_for_resume(resume_id: int, db: Session = Depends(get_db)):
    """查看某简历匹配的所有岗位。"""
    matches = db.query(JobMatch).filter(JobMatch.resume_id == resume_id)\
        .order_by(JobMatch.total_score.desc()).all()
    # ... 返回匹配的岗位列表和分数
```

---

## 六、数据库表结构（完整 DDL）

### 6.1 resumes 表
```sql
CREATE TABLE resumes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    raw_text TEXT,
    parsed_data JSON,
    status ENUM('uploaded','parsed','verified') DEFAULT 'uploaded',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARSET=utf8mb4;
```

### 6.2 resume_fields 表
```sql
CREATE TABLE resume_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resume_id INT UNIQUE NOT NULL,
    name VARCHAR(100),
    phone VARCHAR(20),
    id_card VARCHAR(20),
    email VARCHAR(100),
    education VARCHAR(50),
    school VARCHAR(100),
    major VARCHAR(100),
    graduation_year INT,
    work_experience JSON,
    project_experience JSON,
    skills JSON,
    vector_id VARCHAR(100),
    is_duplicate BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

### 6.3 jobs 表
```sql
CREATE TABLE jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    requirements JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARSET=utf8mb4;
```

### 6.4 job_matches 表
```sql
CREATE TABLE job_matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    resume_id INT NOT NULL,
    keyword_score FLOAT DEFAULT 0,
    semantic_score FLOAT DEFAULT 0,
    total_score FLOAT DEFAULT 0,
    match_details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_resume_id (resume_id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

---

## 七、实施路线图

```
Phase 1 (已完成) ──────────────────────────────
✅ 核心 3 模块功能代码
✅ 模拟数据 + 批量导入
✅ 基础评估脚本

Phase 2 (当前优先) ───────────────────────────
□ A. 测试体系（tests/ 全目录）
□ B. 日志系统（logger.py）
□ C. 全局异常处理（exceptions.py）
□ D. API 响应标准化（schemas/common.py）
□ E. 请求耗时中间件

Phase 3 (质量加固) ───────────────────────────
□ F. 工作年限计算修正
□ G. 上传重名处理
□ H. 分页标准化
□ I. 配置环境分离
□ 简历删除接口
□ 反查匹配接口

Phase 4 (部署就绪) ───────────────────────────
□ J. Dockerfile + docker-compose.yml
□ K. FAISS → Milvus 迁移（可选）
□ L. GitHub Actions CI
□ README 补充部署说明
```

---

## 八、开发规范

### 8.1 代码风格
- Python 3.11+，类型注解使用新语法：`list[str]`、`int | None`
- 遵循 FastAPI 官方推荐的项目结构
- 函数命名：`snake_case`，类命名：`PascalCase`
- 每个 service 函数必须有 docstring

### 8.2 提交规范
```
feat: 新增简历删除接口
fix: 修复工作年限计算偏差
test: 补充 matcher 模块测试
refactor: 提取通用分页响应模型
docs: 更新 API 文档
```

### 8.3 环境要求
- Python 3.11+
- MySQL 8.0+
- PaddleNLP 模型缓存目录需预留 2GB 磁盘
- FAISS 索引文件在 `D:/GitHub/resume_system_data/`（纯英文路径）
