#workers/notification/utils/html_cleaner.py
import re
from bs4 import BeautifulSoup
import html2text


def clean_html(raw_html: str) -> str:
    """
    通用 HTML 清洗器：
    将任何来源的 HTML 源码转换为干净、可读的 Markdown 纯文本。
    """
    if not raw_html:
        return ""

    # 1. 解析
    soup = BeautifulSoup(raw_html, "html.parser")

    # 2. 移除所有非内容标签
    for element in soup(["style", "script", "meta", "head", "title", "link", "noscript"]):
        element.decompose()

    # 3. 移除所有隐藏元素 (这类元素通常是排版干扰或追踪像素)
    # 匹配 display:none, visibility:hidden, max-height:0 等常见隐藏样式
    for hidden_el in soup.find_all(style=lambda v: v and any(
            s in v.replace(' ', '').lower() for s in ['display:none', 'visibility:hidden', 'max-height:0'])):
        hidden_el.decompose()

    # 4. 转换 Markdown
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0

    markdown_text = h.handle(str(soup))

    # 5. 字符清理与换行压缩
    # 处理特殊空白符
    clean_text = re.sub(r'[\u00A0\u200B-\u200D\uFEFF]', ' ', markdown_text)
    # 压缩连续换行
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

    return clean_text.strip()