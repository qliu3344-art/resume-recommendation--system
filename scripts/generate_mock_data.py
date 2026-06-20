"""生成模拟数据：500份简历 + 30个岗位 + 标注数据。"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fpdf import FPDF

# ---------- 基础数据池 ----------

SURNAMES = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴",
            "徐", "孙", "马", "朱", "胡", "郭", "林", "何", "高", "罗"]

GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "洋", "艳",
               "勇", "军", "杰", "涛", "明", "超", "秀英", "华", "慧", "建华",
               "建国", "志强", "志明", "文", "婷", "雪", "浩", "宇", "欣", "怡"]

UNIVERSITIES = {
    "博士": ["清华大学", "北京大学", "浙江大学", "复旦大学", "上海交通大学", "中国科学技术大学"],
    "硕士": ["武汉大学", "华中科技大学", "南京大学", "中山大学", "同济大学", "北京航空航天大学",
             "哈尔滨工业大学", "西安交通大学", "天津大学", "东南大学"],
    "本科": ["四川大学", "山东大学", "厦门大学", "大连理工大学", "华东师范大学", "北京理工大学",
             "中南大学", "湖南大学", "电子科技大学", "重庆大学", "西北工业大学", "兰州大学",
             "中国农业大学", "北京师范大学", "南开大学", "吉林大学"],
    "专科": ["深圳职业技术学院", "南京工业职业技术学院", "天津职业大学", "广州番禺职业技术学院",
             "无锡职业技术学院", "北京电子科技职业学院"],
}

MAJORS = {
    "计算机": ["计算机科学与技术", "软件工程", "人工智能", "数据科学与大数据技术", "信息安全", "物联网工程"],
    "电子": ["电子信息工程", "通信工程", "微电子科学与工程", "光电信息科学与工程"],
    "管理": ["工商管理", "市场营销", "人力资源管理", "会计学", "财务管理"],
    "设计": ["视觉传达设计", "环境设计", "产品设计", "数字媒体艺术"],
    "其他": ["机械工程", "自动化", "土木工程", "材料科学与工程", "生物医学工程", "数学与应用数学"],
}

COMPANIES = [
    "阿里巴巴集团", "腾讯科技", "字节跳动", "百度在线", "京东集团",
    "美团", "滴滴出行", "网易", "小米科技", "华为技术",
    "中兴通讯", "大疆创新", "商汤科技", "旷视科技", "科大讯飞",
    "联想集团", "海尔智家", "比亚迪", "宁德时代", "中芯国际",
    "用友网络", "金蝶软件", "浪潮集团", "深信服科技", "紫光展锐",
    "平安科技", "微众银行", "蚂蚁集团", "携程旅行", "拼多多",
]

POSITIONS = [
    "后端开发工程师", "前端开发工程师", "全栈开发工程师", "移动端开发工程师",
    "数据分析师", "数据工程师", "算法工程师", "机器学习工程师",
    "产品经理", "项目经理", "UI/UX设计师", "交互设计师",
    "测试工程师", "运维工程师", "DevOps工程师", "安全工程师",
    "技术总监", "架构师", "研发经理", "技术顾问",
    "运营专员", "市场专员", "人力资源专员", "财务分析师",
]

SKILLS_POOL = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "Rust",
    "React", "Vue.js", "Angular", "Node.js", "Django", "Flask", "FastAPI",
    "MySQL", "PostgreSQL", "Redis", "MongoDB", "Elasticsearch",
    "Docker", "Kubernetes", "AWS", "阿里云", "Linux",
    "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
    "Git", "CI/CD", "REST API", "GraphQL", "微服务",
    "产品设计", "用户研究", "原型设计", "Figma", "Sketch",
    "项目管理", "敏捷开发", "Scrum", "数据分析", "SQL",
]

EDUCATION_LEVELS = ["专科", "本科", "硕士", "博士"]
EDUCATION_WEIGHTS = [0.15, 0.50, 0.25, 0.10]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RESUME_DIR = os.path.join(BASE_DIR, "data", "resumes")
LABEL_DIR = os.path.join(BASE_DIR, "data", "labels")


def random_phone() -> str:
    prefixes = ["130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
                "150", "151", "152", "153", "155", "156", "157", "158", "159",
                "186", "187", "188", "189"]
    return random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(8)])


def random_id_card() -> str:
    area = str(random.randint(11, 65)) + str(random.randint(0, 20)).zfill(2) + str(random.randint(0, 9)).zfill(2)
    year = random.randint(1975, 2002)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    seq = random.randint(100, 999)
    base = f"{area}{year}{month:02d}{day:02d}{seq}"
    # 简化校验位
    return base + str(random.randint(0, 9))


def random_email(name_pinyin: str) -> str:
    domains = ["qq.com", "163.com", "126.com", "gmail.com", "outlook.com", "foxmail.com"]
    suffix = random.randint(100, 9999)
    return f"{name_pinyin}{suffix}@{random.choice(domains)}"


def generate_resume(resume_id: int, is_dup_of: int | None = None) -> dict:
    """生成一份简历的结构化数据。"""
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_NAMES)
    name = surname + given

    edu = random.choices(EDUCATION_LEVELS, weights=EDUCATION_WEIGHTS, k=1)[0]
    school = random.choice(UNIVERSITIES[edu])
    major_cat = random.choice(list(MAJORS.keys()))
    major = random.choice(MAJORS[major_cat])

    grad_year = random.randint(2005, 2024)
    if edu == "硕士":
        grad_year = random.randint(2008, 2024)
    elif edu == "博士":
        grad_year = random.randint(2010, 2024)

    # 工作经历
    num_jobs = random.randint(1, 4)
    work_exp = []
    start_year = grad_year
    for i in range(num_jobs):
        duration = random.randint(1, 5)
        end_year = min(start_year + duration, 2025)
        company = random.choice(COMPANIES)
        position = random.choice(POSITIONS)
        desc = f"负责{position.replace('工程师', '').replace('师', '')}相关工作，参与核心业务系统开发与维护。"
        work_exp.append({
            "company": company,
            "position": position,
            "period": f"{start_year}-{end_year}",
            "description": desc,
        })
        start_year = end_year

    # 技能
    num_skills = random.randint(5, 15)
    skills = random.sample(SKILLS_POOL, min(num_skills, len(SKILLS_POOL)))

    phone = random_phone()
    id_card = random_id_card()
    email = random_email(f"{surname.lower()}{given.lower()}")

    data = {
        "id": resume_id,
        "name": name,
        "phone": phone,
        "id_card": id_card,
        "email": email,
        "education": edu,
        "school": school,
        "major": major,
        "graduation_year": grad_year,
        "work_experience": work_exp,
        "skills": skills,
    }

    # 如果是重复简历，改一些措辞但保持核心信息不变
    if is_dup_of is not None:
        data["is_duplicate_of"] = is_dup_of

    return data


def generate_resume_text(data: dict) -> str:
    """将结构化数据转为简历文本（用于生成 PDF 和作为 AI 解析输入）。"""
    lines = []
    lines.append(f"姓名：{data['name']}")
    lines.append(f"手机：{data['phone']}")
    lines.append(f"身份证：{data['id_card']}")
    lines.append(f"邮箱：{data['email']}")
    lines.append("")
    lines.append("【教育背景】")
    lines.append(f"{data['graduation_year']}年毕业于{data['school']}，{data['major']}专业，{data['education']}学历。")
    lines.append("")
    lines.append("【工作经历】")
    for exp in data["work_experience"]:
        lines.append(f"{exp['period']}  {exp['company']}  {exp['position']}")
        lines.append(f"  {exp['description']}")
    lines.append("")
    lines.append("【技能】")
    lines.append("、".join(data["skills"]))
    return "\n".join(lines)


def save_resume_pdf(data: dict, resume_id: int):
    """将简历文本保存为 PDF 文件。"""
    text = generate_resume_text(data)
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSC", "", os.path.join(BASE_DIR, "data", "NotoSansSC-Regular.ttf"), uni=True)
    pdf.set_font("NotoSC", size=11)

    for line in text.split("\n"):
        pdf.multi_cell(0, 8, line)

    filepath = os.path.join(RESUME_DIR, f"resume_{resume_id:04d}.pdf")
    pdf.output(filepath)
    return filepath


def save_resume_txt(data: dict, resume_id: int):
    """将简历文本保存为纯文本文件（PDF 生成失败时的备选）。"""
    text = generate_resume_text(data)
    filepath = os.path.join(RESUME_DIR, f"resume_{resume_id:04d}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return filepath


# ---------- 岗位数据 ----------

JOB_TEMPLATES = [
    {"title": "高级后端开发工程师", "description": "负责公司核心业务系统的后端开发，要求具备扎实的后端开发能力和系统架构设计经验。",
     "requirements": {"min_education": "本科", "min_years": 3, "required_skills": ["Python", "MySQL", "Redis"]}},
    {"title": "前端开发工程师", "description": "负责公司Web产品的前端开发，要求熟练掌握主流前端框架。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["JavaScript", "React", "Vue.js"]}},
    {"title": "数据分析师", "description": "负责业务数据分析和可视化，为产品决策提供数据支撑。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Python", "SQL", "Pandas"]}},
    {"title": "算法工程师", "description": "负责机器学习算法的研发与落地，优化推荐系统和搜索排序。",
     "requirements": {"min_education": "硕士", "min_years": 2, "required_skills": ["Python", "TensorFlow", "PyTorch"]}},
    {"title": "产品经理", "description": "负责产品规划和需求分析，推动产品迭代和用户增长。",
     "requirements": {"min_education": "本科", "min_years": 3, "required_skills": ["产品设计", "用户研究", "数据分析"]}},
    {"title": "DevOps工程师", "description": "负责CI/CD流水线建设和容器化部署，保障系统稳定运行。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Docker", "Kubernetes", "Linux"]}},
    {"title": "测试工程师", "description": "负责产品质量保障，编写自动化测试用例，推动测试流程优化。",
     "requirements": {"min_education": "本科", "min_years": 1, "required_skills": ["Python", "Git", "CI/CD"]}},
    {"title": "UI设计师", "description": "负责产品界面设计，输出高质量设计稿，与前端工程师协作完成还原。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Figma", "产品设计", "Sketch"]}},
    {"title": "机器学习工程师", "description": "负责深度学习模型的训练和部署，优化模型推理性能。",
     "requirements": {"min_education": "硕士", "min_years": 1, "required_skills": ["PyTorch", "Python", "Docker"]}},
    {"title": "全栈开发工程师", "description": "负责前后端全链路开发，独立完成功能模块的设计与实现。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["React", "Node.js", "MySQL"]}},
    {"title": "运维工程师", "description": "负责服务器运维和监控，保障线上服务高可用。",
     "requirements": {"min_education": "专科", "min_years": 2, "required_skills": ["Linux", "Docker", "AWS"]}},
    {"title": "安全工程师", "description": "负责公司信息安全体系建设，进行安全漏洞检测和修复。",
     "requirements": {"min_education": "本科", "min_years": 3, "required_skills": ["Python", "Linux", "信息安全"]}},
    {"title": "数据库管理员", "description": "负责数据库运维、性能调优和灾备方案设计。",
     "requirements": {"min_education": "本科", "min_years": 3, "required_skills": ["MySQL", "PostgreSQL", "Redis"]}},
    {"title": "Go后端开发工程师", "description": "使用Go语言开发高性能微服务，负责核心业务逻辑实现。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Go", "Docker", "微服务"]}},
    {"title": "大数据工程师", "description": "负责大数据平台建设和数据处理Pipeline的开发。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Python", "SQL", "Elasticsearch"]}},
    {"title": "技术总监", "description": "负责技术团队管理和技术方向决策，推动技术创新。",
     "requirements": {"min_education": "本科", "min_years": 4, "required_skills": ["项目管理", "微服务", "敏捷开发"]}},
    {"title": "Java开发工程师", "description": "负责Java后端服务开发，参与系统架构设计。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Java", "MySQL", "微服务"]}},
    {"title": "移动端开发工程师", "description": "负责移动端App开发，优化用户体验和性能。",
     "requirements": {"min_education": "本科", "min_years": 1, "required_skills": ["JavaScript", "React", "TypeScript"]}},
    {"title": "云计算架构师", "description": "负责云原生架构设计，优化云资源使用和成本。",
     "requirements": {"min_education": "本科", "min_years": 4, "required_skills": ["AWS", "Kubernetes", "Docker"]}},
    {"title": "NLP工程师", "description": "负责自然语言处理相关算法研发，包括文本分类、实体识别等。",
     "requirements": {"min_education": "硕士", "min_years": 1, "required_skills": ["Python", "PyTorch", "Scikit-learn"]}},
    {"title": "运营专员", "description": "负责产品运营和用户增长，制定运营策略并推动执行。",
     "requirements": {"min_education": "专科", "min_years": 1, "required_skills": ["数据分析", "SQL"]}},
    {"title": "市场经理", "description": "负责市场推广和品牌建设，制定营销策略并跟踪效果。",
     "requirements": {"min_education": "本科", "min_years": 3, "required_skills": ["项目管理", "数据分析"]}},
    {"title": "人力资源专员", "description": "负责招聘、培训和员工关系管理。",
     "requirements": {"min_education": "专科", "min_years": 1, "required_skills": []}},
    {"title": "财务分析师", "description": "负责财务数据分析和报表制作，为管理层提供财务决策支持。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["SQL", "数据分析"]}},
    {"title": "C++开发工程师", "description": "负责底层系统开发和高性能计算模块实现。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["C++", "Linux", "Git"]}},
    {"title": "Rust系统开发工程师", "description": "使用Rust开发高性能系统级应用，关注内存安全和并发性能。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Rust", "Linux", "Git"]}},
    {"title": "数据仓库工程师", "description": "负责数据仓库建模和ETL流程开发。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["SQL", "Python", "数据分析"]}},
    {"title": "SRE工程师", "description": "负责服务可靠性保障，构建监控告警和故障自愈体系。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Linux", "Docker", "Python"]}},
    {"title": "嵌入式开发工程师", "description": "负责嵌入式系统软件开发，包括驱动开发和固件升级。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["C++", "Linux", "Git"]}},
    {"title": "区块链开发工程师", "description": "负责区块链底层开发和智能合约编写。",
     "requirements": {"min_education": "本科", "min_years": 2, "required_skills": ["Go", "Python", "Docker"]}},
]


def generate_all():
    """生成全部模拟数据。"""
    os.makedirs(RESUME_DIR, exist_ok=True)
    os.makedirs(LABEL_DIR, exist_ok=True)

    print("📝 开始生成模拟数据...")

    # 生成 500 份简历
    resumes = []
    dup_groups = []  # 记录重复组 [(原始id, 重复id), ...]

    # 先选 30 个简历作为原始版本（用于生成重复）
    dup_source_ids = random.sample(range(1, 471), 30)

    for i in range(1, 501):
        data = generate_resume(i)
        resumes.append(data)

    # 生成 30 份重复简历（替换最后 30 个 ID 为重复版本）
    for idx, source_id in enumerate(dup_source_ids):
        dup_id = 471 + idx  # 471-500
        source_data = resumes[source_id - 1].copy()
        source_data["id"] = dup_id
        source_data["is_duplicate_of"] = source_id
        # 修改部分措辞但保留核心信息
        source_data["work_experience"] = [
            {**exp, "description": exp["description"].replace("负责", "承担").replace("参与", "协助")}
            for exp in source_data["work_experience"]
        ]
        resumes[dup_id - 1] = source_data
        dup_groups.append((source_id, dup_id))

    # 保存标注数据
    labels = []
    for data in resumes:
        label = {**data}
        label.pop("id", None)
        labels.append({"id": data["id"], "fields": label})

    label_path = os.path.join(LABEL_DIR, "resume_labels.json")
    with open(label_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 标注数据已保存: {label_path}")

    # 保存简历文本文件（用 txt 格式，避免 PDF 字体问题）
    for data in resumes:
        save_resume_txt(data, data["id"])
    print(f"  ✅ {len(resumes)} 份简历文本已保存到 {RESUME_DIR}")

    # 保存岗位数据
    jobs = []
    for i, template in enumerate(JOB_TEMPLATES, 1):
        job = {"id": i, **template}
        jobs.append(job)

    job_path = os.path.join(LABEL_DIR, "jobs.json")
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {len(jobs)} 个岗位已保存: {job_path}")

    # 保存重复组信息
    dup_path = os.path.join(LABEL_DIR, "duplicate_groups.json")
    with open(dup_path, "w", encoding="utf-8") as f:
        json.dump(dup_groups, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {len(dup_groups)} 组重复关系已保存: {dup_path}")

    print(f"\n🎉 模拟数据生成完成:")
    print(f"   - 简历: {len(resumes)} 份（含 {len(dup_groups)} 组重复）")
    print(f"   - 岗位: {len(jobs)} 个")
    print(f"   - 标注: {len(labels)} 条")


if __name__ == "__main__":
    generate_all()
