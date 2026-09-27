"""文件解析。

PDF 侧不能直接按坐标顺序读文本：简历大量使用双栏模板，直接读出来是错乱的
——左栏第一段后面接着右栏第一段，整份简历的语义顺序被打散。

做法是按文本块取坐标，先按横坐标聚类分出栏，再在栏内按纵坐标排序，还原
阅读顺序。不预先判断模板：版面是从块坐标推出来的，不是维护一张模板表。
"""
import os

import fitz  # PyMuPDF
from docx import Document

# 栏间最小间隙占页宽的比例。小于这个值不认为是分栏，只是段落的缩进层级
_COLUMN_GAP_RATIO = 0.08


def _split_columns(blocks: list, page_width: float) -> list[list]:
    """按横坐标把文本块聚成栏，栏内按纵坐标排序。"""
    if len(blocks) < 4:
        return [sorted(blocks, key=lambda b: b[1])]

    # 找横坐标上最大的一段空白，它最可能落在两栏之间
    xs = sorted({round(b[0]) for b in blocks})
    split, gap = None, 0.0
    for left_x, right_x in zip(xs, xs[1:]):
        if right_x - left_x > gap:
            gap, split = right_x - left_x, (left_x + right_x) / 2

    if split is not None and gap >= page_width * _COLUMN_GAP_RATIO:
        left = [b for b in blocks if b[0] < split]
        right = [b for b in blocks if b[0] >= split]
        # 真双栏的结构条件是左右两侧在水平方向上互不重叠。只看间隙大小
        # 会把「正文 + 右对齐的日期」误切成两栏，所以这里必须再验一次。
        if left and right and max(b[2] for b in left) <= min(b[0] for b in right):
            return [
                sorted(left, key=lambda b: b[1]),
                sorted(right, key=lambda b: b[1]),
            ]

    return [sorted(blocks, key=lambda b: b[1])]


def parse_pdf(file_path: str) -> str:
    """解析 PDF 文件，按分栏还原阅读顺序。"""
    pages = []
    with fitz.open(file_path) as doc:
        for page in doc:
            # block_type == 0 是文本块，图片块要在这一步排掉
            blocks = [
                b for b in page.get_text("blocks")
                if b[6] == 0 and isinstance(b[4], str) and b[4].strip()
            ]
            columns = _split_columns(blocks, page.rect.width)
            pages.append("\n".join(b[4].strip() for column in columns for b in column))
    return "\n".join(p for p in pages if p).strip()


def parse_docx(file_path: str) -> str:
    """解析 Word (.docx) 文件，提取全部文本。

    Word 走的是文档结构（段落流），不是 PDF 那种绝对坐标——作者写进去的
    段落顺序就是阅读顺序，不需要重排。PyMuPDF 只负责 PDF，不处理 docx。
    """
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
