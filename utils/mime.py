"""
基于文件内容（魔术头）的 MIME 类型检测，用于自动选择转换器。
"""

import mimetypes
from pathlib import Path
from typing import Optional, Tuple

# 扩展名 -> 标准 MIME（用于 fallback 与统一返回）
_EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}

# 我们支持的 MIME（用于路由）
SUPPORTED_MIMES = frozenset(_EXTENSION_TO_MIME.values())


def detect_mime_from_path(file_path: str | Path) -> Tuple[str, bool]:
    """
    根据文件路径检测 MIME 类型。
    优先用 filetype 读文件头判断，失败时用扩展名推断。

    :param file_path: 文档路径
    :return: (mime_type, from_magic) 其中 from_magic 表示是否由文件头检测得到
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    mime_from_magic: Optional[str] = None
    try:
        import filetype
        kind = filetype.guess(str(path))
        if kind is not None:
            mime_from_magic = kind.mime
    except Exception:
        pass

    if mime_from_magic and mime_from_magic in SUPPORTED_MIMES:
        return mime_from_magic, True

    # 扩展名 fallback
    suffix = path.suffix.lower()
    if suffix in _EXTENSION_TO_MIME:
        return _EXTENSION_TO_MIME[suffix], False

    if mime_from_magic:
        # 能识别但不在支持列表
        raise ValueError(f"不支持的文档类型: {mime_from_magic}，仅支持 PDF, DOCX, PPTX, XLSX。文件: {path}")

    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed in SUPPORTED_MIMES:
        return guessed, False

    if guessed:
        raise ValueError(f"不支持的文档类型: {guessed}，仅支持 PDF, DOCX, PPTX, XLSX。文件: {path}")

    raise ValueError(f"无法识别文件类型: {path}，支持的格式: PDF, DOCX, PPTX, XLSX")


def is_supported_mime(mime: str) -> bool:
    """判断是否为 SDK 支持的 MIME。"""
    return mime in SUPPORTED_MIMES
