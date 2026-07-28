import os

import fitz  # PyMuPDF
from docx import Document


def parse_pdf(file_path: str) -> str:
    """解析 PDF 文件，提取全部文本。"""
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def parse_docx(file_path: str) -> str:
    """解析 Word (.docx) 文件，提取全部文本。"""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def parse_txt(file_path: str) -> str:
    """解析纯文本文件，自动检测编码。"""
    # 优先 UTF-8，失败回退 GBK（中文 Windows 常见）
    for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read().strip()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别文件编码: {file_path}")


def parse_file(file_path: str) -> str:
    """根据文件扩展名自动选择解析器。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return parse_docx(file_path)
    elif ext == ".txt":
        return parse_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
