"""
核心转换逻辑：文档转 Markdown 工具类及便捷函数。
"""

from core.converter import (
    DocumentToMarkdownConverter,
    docx_to_markdown,
    pdf_to_markdown,
    pptx_to_markdown,
    scanned_pdf_to_markdown,
    xlsx_to_markdown,
)

__all__ = [
    "DocumentToMarkdownConverter",
    "pdf_to_markdown",
    "scanned_pdf_to_markdown",
    "docx_to_markdown",
    "pptx_to_markdown",
    "xlsx_to_markdown",
]
