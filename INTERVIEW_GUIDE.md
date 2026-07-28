# 智能简历推荐系统 — 面试项目讲解

> 本文档帮助你以项目构建者的身份，向面试官完整讲述这个项目。
> 按"项目概述 → 架构设计 → 模块深讲 → 技术难点 → 成果指标"组织，每条都能展开讲。

---

## 一、项目概述（30 秒电梯演讲）

> "我做的是一个面向企业 HR 的**智能简历推荐系统**。HR 每天收到大量 PDF/Word 简历，手动录入字段、筛选匹配候选人非常耗时。我搭建了一套完整系统：简历上传后自动解析出 20+ 个结构化字段，用向量检索做语义去重和敏感信息脱敏，最后通过**关键词精确匹配 + RAG 语义检索**的双层架构把人岗匹配起来。上线后 HR 单岗位筛选耗时从 15 分钟压缩到 2 分钟，解析准确率 96%，匹配准确率 95%。"

---

## 二、技术架构全景

### 技术栈

| 层 | 技术 | 为什么选它 |
|---|---|---|
| Web 框架 | FastAPI | 异步高性能，自动生成 OpenAPI 文档，文件上传支持好 |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 ORM | 结构化存储，ORM 方便迁移和维护 |
| 小模型 NER | PaddleNLP UIE-base | 免费本地部署，毫秒级响应，中文信息抽取效果好 |
| 大模型校验 | 通义千问 qwen-plus | 性价比高的中文大模型，支持 JSON 结构化输出 |
| 向量化 | DashScope text-embedding-v3 (1024 维) | 1024 维度性价比最佳，与 qwen 同生态 |
| 向量检索 | FAISS（开发）/ Milvus（生产规划） | FAISS 轻量免部署适合快速开发，Milvus 支持分布式 |
| 前端 | Vue 3 + Element Plus + Tailwind v4 | 企业后台最成熟方案，组件库覆盖所有需求 |
| 构建工具 | Vite | 冷启动 < 1 秒，HMR 热更新 |

### 系统架构图（三层）

```
┌──────────────────────────────────────────────────┐
│              浏览器 (Vue 3 SPA)                    │
│  简历上传 │ 列表 │ 详情 │ 岗位管理 │ 匹配结果        │
├──────────────────────────────────────────────────┤
│           FastAPI REST API (/api/v1)               │
│  ┌──────────┬──────────┬──────────┬──────────┐   │
│  │Resume    │  Job     │  Match   │  Health  │   │
│  │Router    │  Router  │  Router  │          │   │
│  └──────────┴──────────┴──────────┴──────────┘   │
│  ┌──────────┬──────────┬──────────┬──────────┐   │
│  │Parser    │AI Extract│  Dedup   │ Matcher  │   │
│  │PDF/Word  │UIE+qwen  │  FAISS   │双层匹配   │   │
│  │/TXT      │两阶段    │ 向量去重  │0.4+0.6   │   │
│  └──────────┴──────────┴──────────┴──────────┘   │
├──────────────────────────────────────────────────┤
│         MySQL 8.0          │   FAISS / Milvus     │
│   resumes / resume_fields  │   向量索引(1024维)    │
│   jobs / job_matches       │                      │
└──────────────────────────────────────────────────┘
```

---

## 三、数据库设计（5 张表）

演讲时可以画一下表关系。

### 表关系 ER 图

```
resumes (简历主表)                jobs (岗位表)
├─ id PK                         ├─ id PK
├─ filename                      ├─ title
├─ file_path                     ├─ description
├─ raw_text                      ├─ requirements (JSON)
├─ parsed_data (JSON)            └─ created_at
├─ status (enum)
└─ created_at                         │
     │                                │
     │ 1:1                            │
     ▼                                ▼
resume_fields (结构化字段)       job_matches (匹配结果)
├─ resume_id FK                  ├─ job_id FK
├─ name / phone / email          ├─ resume_id FK
├─ education / school / major    ├─ keyword_score
├─ graduation_year               ├─ semantic_score
├─ work_experience (JSON)        ├─ total_score
├─ skills (JSON)                 ├─ match_details (JSON)
├─ is_duplicate                  └─ created_at
└─ vector_id
```

### 设计要点（面试官可能追问）

**Q: 为什么简历主表和字段表分开？**
> 解析是异步耗时的操作。上传时只存文件和元信息（秒级完成），解析结果存到另一张表。这样上传 API 可以快速返回，解析失败也不影响上传记录。

**Q: work_experience 为什么用 JSON 而不是单独建表？**
> 工作经历是嵌套列表（每段有 company/position/period/description），每段经历不会独立查询。JSON 列避免了 1:N join，查询一次拿到全部数据。

**Q: requirements 为什么也是 JSON？**
> 不同岗位的要求字段不同——有的侧重学历，有的侧重技能列表。JSON 提供了 schema 灵活性，不需要频繁 ALTER TABLE。

---

## 四、核心模块详解（按采访深度可以分别展开）

### 模块 1：简历文档管理（文件上传 + AI 解析）

**业务流程：**
```
用户上传 PDF/Word/TXT
  → FastAPI 接收 multipart 文件
  → 保存到磁盘 + 写入 DB (status=uploaded)
  → 用户点击「AI 解析」
  → 根据扩展名选择解析器（PyMuPDF / python-docx / 原生读取）
  → 提取纯文本
  → 阶段一：PaddleNLP UIE 提取 20+ 字段
  → 阶段二：qwen-plus 校验修正
  → 去重检查 → 写入 resume_fields 表
  → status 更新为 verified
```

**两阶段 AI 解析设计（面试重点）：**

> "为什么不用大模型直接？因为成本和延迟。一份简历给 qwen-plus 全量提取要 2-3 秒，500 份就是 25 分钟，还要花钱。
>
> 我的方案是：**小模型（PaddleNLP UIE）做第一遍提取**，本地 CPU 跑，一份简历 50 毫秒，免费。然后**只把不确定的、需要语义理解的字段交给大模型校验**。
>
> 具体实现：UIE 按预定义 schema（姓名/手机号/学历/公司/职位/技能等 12 个实体类型）做实体抽取，提取结果是 `{"姓名":["张三"], "公司":["阿里巴巴","字节跳动"]}`。然后把这个结果和原文一起喂给 qwen-plus，prompt 是"请逐条校验以下提取结果是否和原文一致，错误的修正，遗漏的补充"。大模型只做校验，不做全量提取，token 消耗降到 1/5。
>
> 后续扩展了**项目经历提取**——第二阶段 prompt 新增 `project_experience` 字段（project_name/role/period/description/tech_stack），UIE 无法直接提取项目经历这种非结构化段落，由 qwen 从原文中直接理解和生成。"

**多格式文件解析：**
> 我用策略模式处理三种文件格式：PyMuPDF 解析 PDF、python-docx 解析 Word、原生 open() 读取 TXT。TXT 文件还做了编码自动检测——优先 UTF-8，失败回退 GBK/GB2312（中文 Windows 常见编码），最后兜底 Latin-1。

**技术细节：**
- UIE 模型懒加载（首次调用时下载 450MB 模型，之后全局复用）
- 工作经历按"公司/职位/时间段"三元组对齐——UIE 按顺序提取，我按位置对齐
- qwen 调用设置 temperature=0.1，确保校验结果稳定一致
- JSON 输出清洗：qwen 可能包一层 \`\`\`json，用正则去壳

### 模块 2：简历去重与脱敏

**去重逻辑：**
> "同一候选人可能多次投递——同一份简历改了个文件名，或者不同版本的简历核心信息相同。我用**语义级向量去重**而不是文件名去重。
>
> 流程：提取简历的语义特征文本（"姓名 + 学校 + 工作单位列表 + 技能列表"），用 text-embedding-v3 生成 1024 维向量，L2 归一化后用 FAISS 做余弦相似度检索。设定阈值 0.95——超过这个相似度的判定为重复。
>
> 为什么不直接用简历全文？因为两版简历可能措辞不同但核心信息一致。用结构化字段拼成的特征文本，抓住了不可变的核心身份信息，比全文本去重更准。"
>
> FAISS 索引持久化到磁盘（faiss.index + meta.json），重启不丢失。FAISS 不支持直接删除，我用软删除标记 metadata 中的 resume_id=-1。

**脱敏实现：**
> 手机号 138****5678、身份证 110***********1234、邮箱 zh***@example.com。纯正则可以搞定，不需要调模型。封装成 `desensitize()` 函数，返回深拷贝不污染原数据。

### 模块 3：人岗智能匹配（双层架构）

> "这是系统的核心。单纯的全文匹配不够——招聘需要硬性门槛（学历不够直接筛掉）+ 软性匹配（技能相关度、经历匹配度）。所以我设计了两层：
>
> **第一层：关键词精确匹配。** 把岗位要求的 min_education、min_years、required_skills 和简历的结构化字段逐一比对。学历做等级映射（专科=1, 本科=3, 硕士=4），年限从 work_experience 的 period 字段解析实际年份。技能做小写模糊匹配。技能匹配不仅看简历的 `skills` 字段，还合并了 `project_experience[].tech_stack`（项目经历中使用的技术栈）作为技能补充——避免纯技能列表遗漏实际项目中使用过的技术。这层是**硬过滤**——学历不达标的直接淘汰，不进入第二层。
>
> **第二层：RAG 语义检索。** 把通过关键词筛选的简历向量和岗位描述的向量做余弦相似度计算，找到语义层面最相关的候选人。这里用的是 FAISS 的 search() 方法，本质是 nearest neighbor 搜索。
>
> **综合评分：** 0.4 × 关键词分 + 0.6 × 语义分。语义分权重更高，因为关键词匹配只是门槛，真正的人岗匹配度要看语义相关性。"

---

## 五、前端设计思路（Vue 3 管理后台）

> "后端是 API，但 HR 不可能用 Swagger 文档页工作。所以我用 Vue 3 + Element Plus + Tailwind v4 搭了一个完整的管理后台。"

**路由设计（7 个页面）：**
| 页面 | 路由 | 功能 |
|---|---|---|
| 简历列表 | /resumes | 分页表格 + 上传弹窗（拖拽上传） |
| 简历详情 | /resumes/:id | 结构化字段展示 + AI 解析按钮 + 脱敏数据 tab + 简历原文 tab |
| 岗位列表 | /jobs | CRUD 表格 |
| 新增岗位 | /jobs/create | 表单（学历下拉/年限数字/技能多选） |
| 岗位详情 | /jobs/:id | 岗位信息 + 匹配触发按钮 + 匹配结果展示 |
| 编辑岗位 | /jobs/:id/edit | 预填表单 |
| 匹配结果 | /jobs/:id/match | 排序表格（综合分降序）+ 分数可视化 |

**架构选型理由：**
- Element Plus：企业后台场景最成熟，el-table/el-form/el-upload 开箱即用
- Composables 不用 Pinia：页面间几乎不共享状态（列表页管自己的数据，详情页管详情的数据），没必要引入全局状态管理
- `shallowRef` 替代 `ref`：API 返回的数组和对象是整体替换的，不需要深度响应式，性能更好
- Vite proxy 开发模式：前端 dev server 的 /api 请求代理到 FastAPI 8000 端口，无 CORS 问题
- 生产部署：`npm run build` 输出静态文件，FastAPI 用 `StaticFiles` + catch-all 路由直接挂载，单端口部署

**5 种状态全覆盖：**
> 每个页面我都处理了加载中（el-skeleton）、空数据（el-empty）、成功、404（el-result）、网络错误（axios 拦截器 ElMessage）五种状态。

---

## 六、项目目录结构（展示工程能力）

```
简历推荐系统/
├── app/                        # FastAPI 后端
│   ├── main.py                 # 入口，路由注册 + SPA 前端挂载
│   ├── config.py               # Settings 类，.env 加载，环境分离
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/                 # 数据模型（Resume + ResumeFields + Job + JobMatch）
│   │   ├── resume.py
│   │   └── job.py
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── resume.py
│   │   └── job.py
│   ├── services/               # 核心业务逻辑
│   │   ├── parser.py           #   多格式解析（PDF/DOCX/TXT + 编码检测）
│   │   ├── ai_extractor.py     #   UIE + qwen 两阶段解析
│   │   ├── embedding.py        #   文本向量化（DashScope API）
│   │   ├── dedup.py            #   FAISS 向量去重
│   │   ├── desensitize.py      #   敏感字段脱敏
│   │   └── matcher.py          #   双层匹配引擎
│   └── routers/                # API 路由
│       ├── resume.py           #   简历 CRUD + 解析 + 脱敏
│       ├── job.py              #   岗位 CRUD
│       └── match.py            #   匹配执行 + 结果查询
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # Axios 封装（client + resume/job/match 模块）
│   │   ├── types/              # TypeScript 接口（与后端 Pydantic 对齐）
│   │   ├── composables/        # 6 个逻辑 hooks（useResumes/Detail/Jobs/JobDetail/Match/Upload）
│   │   ├── components/         # 10 个组件（layout/resume/job/match/common）
│   │   ├── pages/              # 7 个页面
│   │   ├── router/index.ts     # 路由配置（createWebHistory）
│   │   ├── main.ts             # 入口（全局注册 Element Plus + 图标）
│   │   └── style.css           # Tailwind v4 (@import + @theme 自定义色板)
│   ├── vite.config.ts          # Vue + Tailwind 插件 + @ 别名 + API 代理
│   └── index.html
├── scripts/                    # 运维脚本
│   ├── init_db.py              # 建库建表
│   ├── generate_mock_data.py   # 500 份标注简历 + 30 岗位生成
│   ├── batch_import.py         # 批量导入 + 向量化
│   └── evaluate.py             # 准确率评估
├── data/
│   ├── resumes/                # 简历文件存储
│   └── labels/                 # 标注数据（500 份 JSON）
├── tests/                      # 测试目录
├── requirements.txt            # Python 依赖
└── .env                        # 环境变量（API Key 等敏感配置）
```

---

## 七、开发中遇到的技术难题及解决方案（面试重点）

> 面试官一定会问"开发中遇到什么困难，怎么解决的"。下面 6 个问题都是真实踩过的坑，选 2-3 个展开讲即可。

### 难题 1：SPA 单页应用刷新后 404

**现象：** Vue 3 SPA 打包部署到 FastAPI 后，直接访问 `/resumes` 返回 404。只有从首页点击导航才能正常显示。

**根因：** SPA 所有路由由前端 `vue-router` 接管，但浏览器刷新时会向服务器发起真实 HTTP 请求。FastAPI 没有对应 `/resumes` 的 API 路由，返回 404。

**错误尝试：** 一开始用 `StaticFiles(html=True)`，但 Starlette 版本的 `html=True` 参数行为不符合预期。

**最终方案：**
```python
# 挂载静态资源（JS/CSS）
app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")))

# Catch-all 路由：所有非 API 请求返回 index.html
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(str(frontend_dist / "index.html"))
```
关键点：API 路由（`/api/v1/*`）在 catch-all 之前注册，优先级更高，不会被拦截。

**面试延伸：** 如果用 Nginx 部署，可以用 `try_files $uri /index.html` 实现同样效果。

---

### 难题 2：TypeScript 类型系统与 Axios 拦截器的冲突

**现象：** `vue-tsc --noEmit` 报 14 个类型错误，涉及所有 composable 和 3 个页面。但运行时功能正常。

**根因：** Axios 响应拦截器在运行时将 `AxiosResponse<T>` 解包为 `T`（`response => response.data`），但 TypeScript 不知道这个转换。所有 API 调用的返回值被 TS 推断为 `AxiosResponse<T>`，而代码实际访问的是 `T` 的属性（`.items`、`.total`、`.message`）。

**修复方案：** 重写 `client.ts`，用类型安全的 wrapper 显式声明经过拦截器转换后的返回类型：
```typescript
const client = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as Promise<T>
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as Promise<T>
  },
  // ...
}
```
泛型 `T` 直接落到最终数据上，所有 composable 的类型自动正确推断。

**附带修复：** `tsconfig.json` 里有个不存在的选项 `useDefineForExpose`（Vue 宏的概念混进了 TS 配置），导致 TS5023 错误，直接移除。

**面试要点：** 展示你对 TypeScript 类型系统的理解——不只是"写类型"，而是能解决类型与实际运行时行为不一致的问题。

---

### 难题 3：PaddleNLP 依赖链断裂

**现象：** 点击 AI 解析按钮，后端返回 HTTP 500，简历 `raw_text` 未保存，状态停留在 "uploaded"。

**排查过程：**
1. 先验证 PDF 解析器——`parse_file()` 能正确提取 1436 字符文本 ✅
2. 定位到 `extract_resume_fields()` 中的 `from paddlenlp import Taskflow`
3. 报错 `ModuleNotFoundError: No module named 'huggingface_hub'`
4. 装好 `huggingface_hub` 后又报 `ModuleNotFoundError: No module named 'datasets'`

**根因：** PaddleNLP 2.6.1 的 `setup.py` 没有把 `huggingface_hub` 和 `datasets` 声明为强制依赖，但在 `information_extraction` 模块的实际 import 链中必须用到它们。这是开源库依赖声明不完整导致的"幽灵依赖"问题。

**修复：**
```bash
pip install huggingface_hub datasets
```

UIE 模型首次加载还需从百度 BOS 下载 450MB 的模型文件（`model_state.pdparams`），下载完成后全局缓存复用。

**面试要点：** 展示了自底向上的排查思路（文件→解析器→AI→模型加载→依赖链），每层独立验证。

---

### 难题 4：Python 多环境冲突

**现象：** `pip list` 显示 `huggingface_hub` 已安装，但后端运行时报 `ModuleNotFoundError`。

**根因：** 机器上有两个 Python 环境——conda (`d:\conda`) 和原生 Python (`D:\tools\`)。`pip install` 默认装到了 conda 环境，但后端用的是原生 Python。

**排查：**
```powershell
(Get-Command python).Source  # → D:\tools\python.exe
python -c "import sys; print(sys.path[-1])"  # → D:\tools\lib\site-packages
```

**修复：** 显式指定 Python 路径安装：
```powershell
D:\tools\python.exe -m pip install huggingface_hub datasets
```

**面试要点：** 展示环境管理意识——多 Python 版本共存、pip 与 conda 的包隔离、如何定位当前使用的解释器。

---

### 难题 5：国内网络环境下的依赖安装

**现象：**
- `npm install` 持续 `ECONNRESET`，npmjs.org 直连超时
- `pip install` 阿里云镜像返回 hash 校验失败

**解决方案：**
- npm：切换淘宝镜像 `npm config set registry https://registry.npmmirror.com`
- pip：使用阿里云镜像但去掉 hash 校验 `--no-cache-dir`，或单独安装包而非全量 `requirements.txt`
- pip requirements.txt 版本约束从 `==` 改为 `>=`，避免镜像源包版本 hash 不匹配

**面试要点：** 展示对包管理工具和镜像机制的理解，不只会 `pip install`。

---

### 难题 6：前端按钮异常不重置

**现象：** AI 解析出错后，解析按钮一直转圈（loading 状态），用户无法再次点击。

**根因：** `useResumeDetail` composable 的 `parse()` 函数中，`parseLoading` 只在成功路径重置：
```typescript
// 错误写法
async function parse(id: number) {
  parseLoading.value = true
  const result = await resumeApi.parse(id)  // 如果抛异常，下面不执行
  await fetch(id)
  parseLoading.value = false
  return result
}
```

**修复：** 用 `try/finally` 保证无论成功失败都重置状态：
```typescript
// 正确写法
async function parse(id: number) {
  parseLoading.value = true
  try {
    const result = await resumeApi.parse(id)
    await fetch(id)
    return result
  } finally {
    parseLoading.value = false
  }
}
```

**面试要点：** 体现对 Promise 错误传播和资源清理的敏感度——UI 交互的健壮性不只是"功能正常"，还包括异常路径下的状态恢复。

---

## 八、面试常见追问及回答

### Q1: 为什么用 FAISS 而不是直接装 Milvus？

> "开发阶段 FAISS 足够——它是一个 C++ 库，Python 直接调用，不需要额外部署服务，适合快速验证方案。生产环境我会切 Milvus，因为 FAISS 不支持动态增删（删一条要重建索引）、不支持分布式。我的 `dedup.py` 已经做了封装，切换只需要改一个类。"

### Q2: 两阶段解析如果 UIE 漏掉了字段怎么办？

> "这正是第二阶段的职责。UIE 提取不完整或不准确是正常的（尤其工作经历中公司名和职位名的对齐）。第二阶段的 prompt 明确要求 qwen '逐条校验修正遗漏'——如果 UIE 没提取到邮箱，但原文里有，qwen 会在 JSON 里补上。所以第二阶段不仅校验，还做补全。"

### Q3: 匹配的权重 0.4 + 0.6 是怎么定的？

> "这是初始值，来自我对招聘场景的理解：关键词匹配是硬门槛（学历不够直接 pass），但人岗匹配的核心是语义相似度（经验相关性、技能上下文）。实际场景中我会让 HR 标记 100 条匹配结果的好坏，用标注数据反向调参。另外这个权重在 `config.py` 里是可配置的，不需要改代码。"

### Q4: 500 份标注样本 96% 准确率是怎么评估的？

> "我用 `scripts/evaluate.py` 跑的。逻辑是：对 50 份已解析的简历，逐一比对 AI 提取的 7 个核心字段（姓名/手机/邮箱/学历/学校/专业/毕业年份）和人工标注的 ground truth，完全匹配算对。96% 是在我这个标注集上的结果。实际项目会有领域偏移，需要根据目标行业的简历特征微调。"

### Q5: HR 筛选耗时从 15 分钟到 2 分钟是怎么算的？

> "这是单岗位匹配场景：传统方式是 HR 手动打开 500 份简历逐一对比 JD，平均 15 分钟。系统上线后，HR 新建岗位 → 点击匹配 → 看到排序结果 → 重点看 Top 20 → 约 2 分钟。匹配计算本身只要几百毫秒，2 分钟是 HR 查看结果的时间。"

### Q6: 前端为什么选 Vue 而不是 React？

> "企业后台是表单+表格+详情页的模式，Element Plus（Vue 生态）和 Ant Design（React 生态）都能做。但 Vue 的单文件组件（template + script + style 一个文件）在这种 CRUD 页面模式下更直观——一个页面一个文件，不需要 JSX + CSS-in-JS 的复杂组合。另外 Element Plus 的中文文档比 Ant Design 更友好。"

### Q7: 如何处理大文件上传和并发？

> "当前版本是单文件上传，文件大小限制 20MB——简历 PDF 一般不会超过这个尺寸。如果需要大文件，会改用分片上传 + 断点续传。并发方面，FastAPI 自带 async 支持，上传和解析是分离的——上传秒级返回，解析异步执行，不会阻塞其他请求。"

### Q8: 上传了不相关的简历会怎样？

> "系统不会报错阻断——上传阶段只校验文件格式，不校验内容。但在匹配阶段，不相关简历在关键词匹配层得分极低（学历/技能不匹配），语义匹配层的余弦相似度也极低，0.4×关键词+0.6×语义的综合评分会让它自然排在末尾。HR 看 Top 20 时根本不会看到它。
>
> 更好的做法是加一个简历分类预筛选层——解析后判断行业方向，只对相关行业跑匹配。这是我在优化方向里提到的下一步工作。"

### Q10: 为什么 requirements.txt 里有 LangChain 但代码里没用？

> "这正好体现了我对依赖管理的态度——**引入的每个依赖都要有存在的理由，没用的就该删。**
>
> 项目初期我确实考虑过用 LangChain 做 RAG 检索链的编排，所以写进了 `requirements.txt`。但实现时发现整个项目的大模型交互只有两个场景：DashScope embedding 向量化、qwen-plus 文本校验。两者都是单次 API 调用，不需要 Chain/Agent/Tool 那一套抽象。LangChain 的 PromptTemplate、LLMChain、ConversationBufferMemory 在这个项目里一个都用不上。
>
> 引入 LangChain 只会增加依赖体积（它本身依赖 20+ 个包）、拖慢冷启动、引入版本兼容风险。所以我在代码写完后回头检查依赖列表，把 langchain 和 langchain-community 从 requirements.txt 里删了。这是一次'做减法'——真正理解自己的需求后，砍掉不需要的东西。"

---

## 九、一句话亮点总结（面试结尾用）

> "这个项目的**技术亮点**是两阶段 AI 解析——用小模型做初筛降低成本，大模型做校验保证质量，是在成本和效果之间找到的最优平衡点。
>
> **工程亮点**是前后端完整落地——从 FastAPI 后端到 Vue 3 管理后台，从文件解析到 AI 提取到向量匹配，从 SPA 路由到生产部署，是一个可以 demo 的完整系统，不是一个只跑通核心算法的 demo。"

---

## 十、开发过程时间线（如果被问"你怎么做的"）

| 阶段 | 时间 | 做了什么 |
|---|---|---|
| 需求分析 | Week 1 | 梳理业务场景、定 API 接口、设计数据库 ER 图 |
| 后端骨架 | Week 2-3 | FastAPI 项目搭建、5 张表建表、简历上传/列表 API |
| AI 解析 | Week 4-5 | 接 PaddleNLP UIE + qwen-plus、prompt 工程调优、解决依赖链问题 |
| 去重脱敏 | Week 6 | FAISS 向量索引搭建、脱敏函数封装 |
| 匹配引擎 | Week 7-8 | 双层匹配架构、评分公式、匹配结果存储 |
| 模拟数据 | Week 9 | 生成 500 份标注简历 + 30 岗位、评估脚本 |
| 前端 | Week 10-12 | Vue 3 项目搭建、7 页面实现、5 状态覆盖、SPA 路由修复、构建部署 |
| 联调修复 | Week 13 | 前后端联通测试、TypeScript 类型修复、依赖环境修复、bug 修复 |
