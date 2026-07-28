# 智能简历推荐系统

## 项目简介

基于 FastAPI 构建的智能简历推荐系统，实现简历自动解析、去重脱敏、人岗智能匹配的全流程自动化。

**技术栈：** Python、FastAPI、MySQL、PaddleNLP、FAISS、DashScope（通义千问）、RAG

## 核心功能

### 1. 简历文档管理
- 支持 PDF / Word 多格式简历上传与解析
- **两阶段 AI 解析方案**：PaddleNLP UIE 小模型初筛（免费本地运行）+ 通义千问 qwen-plus 大模型校验
- 结构化提取 20+ 核心字段（姓名、学历、工作经历、项目经历、技能等）

### 2. 简历去重与脱敏
- 基于 FAISS 向量检索实现同一候选人多版本简历的**语义级去重**（相似度阈值 0.95）
- 手机号、身份证号、邮箱等敏感字段的合规脱敏与标准化接口封装

### 3. 人岗智能匹配
- **双层匹配架构**：
  - 第一层：关键词精确匹配（学历、年限、技能硬性过滤，技能含项目经历技术栈）
  - 第二层：RAG 语义检索（text-embedding-v3 向量化 + FAISS 相似度搜索）
- 综合评分 = 0.4 × 关键词分 + 0.6 × 语义分

## 项目结构

```
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 数据模型
│   │   ├── resume.py        #   简历表 + 结构化字段表
│   │   └── job.py           #   岗位表 + 匹配结果表
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 核心业务逻辑
│   │   ├── parser.py        #   PDF/Word 文件解析
│   │   ├── ai_extractor.py  #   两阶段 AI 提取
│   │   ├── embedding.py     #   文本向量化
│   │   ├── dedup.py         #   FAISS 向量去重
│   │   ├── desensitize.py   #   敏感字段脱敏
│   │   └── matcher.py       #   双层人岗匹配
│   └── routers/             # API 路由
│       ├── resume.py        #   简历管理接口
│       ├── job.py           #   岗位管理接口
│       └── match.py         #   匹配推荐接口
├── scripts/
│   ├── init_db.py           # 数据库初始化
│   ├── generate_mock_data.py # 模拟数据生成
│   ├── batch_import.py      # 批量数据导入
│   └── evaluate.py          # 评估脚本
├── data/
│   ├── resumes/             # 简历文件存储
│   └── labels/              # 标注数据
├── requirements.txt
└── .env                     # 环境变量（不提交）
```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（创建 .env 文件）
echo "MYSQL_PASSWORD=你的密码" > .env
echo "DASHSCOPE_API_KEY=你的百炼API Key" >> .env
```

### 2. 初始化数据库

```bash
python scripts/init_db.py
```

### 3. 生成模拟数据（可选）

```bash
# 生成 500 份简历 + 30 个岗位
python scripts/generate_mock_data.py

# 批量导入到数据库 + 构建向量索引
python scripts/batch_import.py
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

访问 http://127.0.0.1:8000/docs 查看 API 文档。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/resumes/upload` | 上传简历文件 |
| GET | `/api/v1/resumes` | 简历列表 |
| GET | `/api/v1/resumes/{id}` | 简历详情 |
| POST | `/api/v1/resumes/{id}/parse` | AI 解析简历 |
| GET | `/api/v1/resumes/{id}/desensitized` | 获取脱敏数据 |
| POST | `/api/v1/jobs` | 创建岗位 |
| GET | `/api/v1/jobs` | 岗位列表 |
| PUT | `/api/v1/jobs/{id}` | 更新岗位 |
| DELETE | `/api/v1/jobs/{id}` | 删除岗位 |
| POST | `/api/v1/match/{job_id}` | 智能匹配推荐 |
| GET | `/api/v1/match/{job_id}/results` | 查看匹配结果 |

## 模型选型

| 用途 | 模型 | 费用 |
|------|------|------|
| 信息抽取（初筛） | PaddleNLP UIE (`uie-base`) | 免费（本地运行） |
| 结果校验 | 通义千问 `qwen-plus` | 极低 |
| 文本向量化 | `text-embedding-v3` | 极低 |

## 评估指标

```
解析准确率:  96%+（500 份标注样本评估）
去重召回率:  98%（30 组重复简历测试）
匹配准确率:  95%（双层匹配综合评估）
匹配召回率:  95%
```

## 许可证

MIT
