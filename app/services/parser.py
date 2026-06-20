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


def parse_file(file_path: str) -> str:
    """根据文件扩展名自动选择解析器。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return parse_docx(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
