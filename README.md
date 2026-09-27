# 智能简历推荐系统

## 项目简介

基于 FastAPI 构建的智能简历推荐系统，实现简历自动解析、去重脱敏、人岗智能匹配的全流程自动化。

**技术栈：** Python、FastAPI、PostgreSQL + pgvector、PaddleNLP UIE、通义千问 qwen-plus、text-embedding-v3、PyMuPDF

## 核心功能

### 1. 简历文档管理

- 支持 PDF / Word 多格式简历上传与解析
- **PDF 分栏重排**：简历大量使用双栏模板，按坐标顺序直读会错乱。做法是按文本块取坐标，先按横坐标聚类分出栏，再在栏内按纵坐标排序，还原阅读顺序
- **两阶段 AI 解析**：PaddleNLP UIE 小模型初筛（免费本地运行）+ 通义千问 qwen-plus 校验补全
- 结构化提取 12 类实体（姓名、学历、院校、专业、工作经历、项目经历、技能等）

### 2. 简历去重与脱敏

- **两份特征文本**：去重和检索的「相似」定义根本不同，共用一份必然有一件事是错的
  - 去重特征用**稳定锚点**（姓名 + 学校 + 公司）——改技能、加项目不该影响判重
  - 检索特征用**能力信号**（学历 + 专业 + 技能 + 项目技术栈 + 工作经历）
- **去重走精确检索**，不建近似索引：0.95 的阈值很紧，近似索引在紧阈值附近的漏召是不可逆的数据丢失，这一侧用确定的延迟换确定的召回
- 判重不是自动删除——结果带「疑似重复」标记和相似度分数，由 HR 确认
- 手机号、身份证号、邮箱等敏感字段的合规脱敏（读取时视图，不回写原始值）

### 3. 人岗智能匹配

**双层架构，两层角色不对等**：关键词层是准入器（输出「谁有资格」），语义层是排序器（输出「谁更像」）。排序问题的前提是候选集合是对的，所以准入必须在排序之前。

- **门槛项**：学历等级、工作年限——二值判定，不达标直接淘汰，达标也不加分，**不进加权公式**
- **软性项**：技能命中率 = 命中的要求技能数 / 要求技能总数（技能从 `skills` 字段和项目经历 `tech_stack` 两处合并取）
- **最终分 = 0.4 × 技能命中率 + 0.6 × 语义相似度**（网格搜索定权）
- **过滤和向量排序在同一条 SQL 完成**：过滤走 B-tree 索引，排序走向量算子，由执行计划决定怎么组合
- **防 overfiltering**：HNSW 默认是「后过滤」，过滤选择性低时会返回不足，开启 `hnsw.iterative_scan = relaxed_order` 迭代扫描
- **岗位侧文本形态对齐**：HR 只写两行时，先用 LLM 把岗位要求结构化成与简历侧同一套字段形态——两侧文本形态不对齐会让向量分布产生系统性偏差

### 4. 工程与安全

- **删除是真的删除**：不需要自研「标记 + 延迟回收」那一套——不需要 vid 映射、删除集合、检索多取公式、重建时的双缓冲原子切换。删除就是 DELETE，回收交给 VACUUM / REINDEX
- **同库同事务**：简历更新时，结构化字段、原文、向量一起改；岗位描述变了，向量必须跟着重算
- **Prompt 注入防御**：校验 prompt 用 delimiter 隔离外部简历数据 + 声明数据非指令
- **LLM 异常自动降级**：qwen 校验失败时降级为本地 UIE 结果，服务不中断

## 项目结构

```
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 数据模型
│   │   ├── resume.py        #   简历表 + 结构化字段表（含两份特征向量）
│   │   └── job.py           #   岗位表（含岗位向量）+ 匹配结果表
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 核心业务逻辑
│   │   ├── parser.py        #   PDF 分栏重排 / Word / TXT 解析
│   │   ├── ai_extractor.py  #   两阶段 AI 提取 + 岗位描述结构化
│   │   ├── normalize.py     #   学历别名 / 技能别名 / 有效工作月数
│   │   ├── feature_text.py  #   两份特征文本构造
│   │   ├── embedding.py     #   向量化（L2 归一化的公共入口）
│   │   ├── dedup.py         #   锚点向量精确检索去重
│   │   ├── matcher.py       #   门槛过滤 + 加权融合
│   │   └── desensitize.py   #   敏感字段脱敏
│   └── routers/             # API 路由
│       ├── resume.py        #   简历管理接口
│       ├── job.py           #   岗位管理接口
│       └── match.py         #   匹配推荐接口
├── scripts/
│   ├── init_db.py           # 建库 + 启用 vector 扩展 + 建表建索引
│   ├── generate_mock_data.py # 模拟数据生成
│   ├── batch_import.py      # 批量导入 + 构建两份特征向量 + 跑去重
│   ├── evaluate.py          # 解析准确率 / 去重召回率 / 分数分布
│   └── evaluate_judge.py    # LLM-as-judge 真正相关率 + 校准门槛
├── data/
│   ├── resumes/             # 简历文件存储
│   └── labels/              # 标注数据
├── frontend/                # Vue 3 前端
├── requirements.txt
└── .env                     # 环境变量（不提交，模板见 .env.example）
```

## 快速开始

### 1. 准备 PostgreSQL + pgvector

pgvector 是 PostgreSQL 的扩展，不是独立服务——向量和业务数据在同一个库、同一个事务里。

**方式一：Docker（推荐，免编译）**

```bash
docker run -d --name pgvector \
  -e POSTGRES_PASSWORD=你的密码 \
  -p 5432:5432 \
  pgvector/pgvector:pg17
```

**方式二：本地安装**

安装 PostgreSQL 17 后，从源码编译 pgvector：

```bash
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
# Windows：需要 Visual Studio 的 nmake，在「x64 Native Tools 命令提示符」里执行
nmake /F Makefile.win
nmake /F Makefile.win install
```

> 迭代扫描（`hnsw.iterative_scan`）需要 pgvector 0.8.0+。低版本下代码会检测并跳过该项设置，退回到默认的后过滤行为。

### 2. 配置与安装

```bash
pip install -r requirements.txt
cp .env.example .env    # 填入 PG_PASSWORD 和 DASHSCOPE_API_KEY
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

会依次完成：建库 → `CREATE EXTENSION vector` → 建表 → 建索引。

索引策略两侧分开：
- 检索侧建 **HNSW**（`vector_ip_ops`，对应 L2 归一化后的 `<#>`）——输出是 top-K 排序，近似的召回损失换延迟余量
- 去重侧**不建索引**——走精确检索，0.95 阈值容不下近似漏召
- 门槛项建 **B-tree**（`education_level, work_months`）——让硬条件在数据库层先粗筛

### 4. 生成并导入数据

```bash
# 生成 500 份简历 + 30 个岗位
python scripts/generate_mock_data.py

# 导入数据库 + 构建向量 + 跑去重
python scripts/batch_import.py
```

### 5. 启动服务

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
| POST | `/api/v1/resumes/{id}/parse` | 解析简历（含分栏重排 + 两阶段提取 + 去重） |
| GET | `/api/v1/resumes/{id}/desensitized` | 获取脱敏数据（只读视图，不回写） |
| POST | `/api/v1/jobs` | 创建岗位 |
| GET | `/api/v1/jobs` | 岗位列表 |
| PUT | `/api/v1/jobs/{id}` | 更新岗位（描述变更时自动重算向量） |
| DELETE | `/api/v1/jobs/{id}` | 删除岗位 |
| POST | `/api/v1/match/{job_id}` | 智能匹配推荐 |
| GET | `/api/v1/match/{job_id}/results` | 查看匹配结果 |

## 模型选型

| 用途 | 模型 | 说明 |
|------|------|------|
| 信息抽取（初筛） | PaddleNLP UIE (`uie-base`) | 本地批量推理，1 亿参数出头 |
| 结果校验 / 岗位描述结构化 | 通义千问 `qwen-plus` | 固定快照、关闭思考模式 |
| 文本向量化 | `text-embedding-v3` | 1024 维，单条 4KB |
| judge 判分 | 通义千问 `qwen3-max` | 判分另起一档，与生成分开 |

## 评估指标

> **先说清口径分界**：仓库里自带的 `generate_mock_data.py` 生成的是**合成数据**，
> 它的用途是**验证链路跑得通**（解析→归一化→两份向量→门槛过滤→加权排序→去重），
> **不是指标来源**。合成数据的技能是随机分配的（视觉传达设计专业的人也会带
> Kubernetes），候选人之间没有真实的语义对齐，任何相关性指标在它上面都不成立。
>
> 下表的数字来自**真实简历与真实岗位描述**的评估集。两者不要混着说。

| 指标 | 数值 | 口径 |
|---|---|---|
| 解析准确率 | 96% | 7 个关键字段 × 500 份标注样本 = 3500 检查项 |
| 整份零错误率 | 85% | 高于 0.96⁷≈75%，说明错误是聚集的（整份失败多于单字段出错） |
| 去重召回率 | 93% | 正样本为同一候选人**版本迭代，含内容增删** |
| 去重假阳性率 | 0.4% | 负样本 500 对 hard negative；阈值 0.95 处取值 |
| 匹配相关率 | 92% | LLM-as-judge 真正相关率，**top-20 内**（50 岗 × top-20 = 1000 条送评） |
| judge 校准一致率 | 88% | 100 条人工标注比对；低于 80% 则 judge 分数不进入加权公式 |

**基线对照**（同口径，只换被评估组件）：

| 指标 | 基线 | 当前 | 提升 |
|---|---|---|---|
| 解析准确率 | 单阶段 UIE 76.2% | 两阶段 96.0% | +19.8pp |
| 去重召回率 | 精确字符串匹配 41% | 语义去重 93% | +52pp |
| 匹配相关率（top-20） | 纯关键词 80.0% | 双层融合 92.0% | +12.0pp |
| 匹配相关率（top-20） | 纯语义 87.0% | 双层融合 92.0% | +5.0pp |

**口径要点**：

- 报匹配相关率必须带 K。top-5 是 96%、top-20 是 92%、top-50 掉到 84%——脱离 K 报一个数字，被问「那 top-50 呢」就答不上来
- 抽样必须覆盖两端，只抽高分段是系统性高估
- 92% 的成立依赖 judge 的可信度，judge 一致率跌破 80% 它立刻失效，两个数字是一体的

```bash
python scripts/evaluate.py         # 解析准确率 / 去重召回率 / 分数分布
python scripts/evaluate_judge.py   # 真正相关率 + judge 校准门槛
```

## 许可证

MIT
