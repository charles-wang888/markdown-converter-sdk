"""
工具函数：MIME 检测等。
"""

from utils.mime import (
    SUPPORTED_MIMES,
    detect_mime_from_path,
    is_supported_mime,
)

__all__ = ["detect_mime_from_path", "is_supported_mime", "SUPPORTED_MIMES"]
