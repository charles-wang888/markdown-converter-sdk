"""
转换与 OCR 配置：PDF OCR 后端枚举及选项；文档内嵌图片导出模式。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ImageExportMode(str, Enum):
    """文档内嵌图片在导出为 Markdown 时的处理方式（对应 docling --image-export-mode）。"""

    # 图片导出到外部目录（如 xxx_artifacts），MD 中以相对路径引用；推荐
    REFERENCED = "referenced"
    # 图片以 Base64 内嵌到 MD 中；不推荐，资源与主文件应分开存放
    EMBEDDED = "embedded"


class OcrBackend(str, Enum):
    """PDF 处理时可选的 OCR 引擎。"""

    # Docling 内置
    AUTO = "auto"  # 自动选择
    RAPID_OCR = "rapid_ocr"
    EASY_OCR = "easy_ocr"
    TESSERACT = "tesseract"
    TESSERACT_CLI = "tesseract_cli"
    OCR_MAC = "ocr_mac"  # 仅 macOS

    # RapidOCR 的 Paddle 后端，即使用 PaddleOCR 模型
    PADDLE_OCR = "paddle_ocr"

    # 以下需额外环境或自定义集成，当前映射到最接近的内置方案或预留
    MINER_U = "miner_u"  # 文档级流水线，可后续对接 MinerU 外部调用
    DEEPSEEK_OCR = "deepseek_ocr"  # API 型，可后续对接


@dataclass
class PdfOcrConfig:
    """PDF OCR 配置。"""

    # 是否启用 OCR（扫描版 PDF 建议 True，常规 PDF 可为 False）
    do_ocr: bool = True
    # 使用的 OCR 后端
    backend: OcrBackend = OcrBackend.RAPID_OCR
    # RapidOCR 推理后端: onnxruntime, openvino, paddle, torch
    rapid_ocr_backend: str = "onnxruntime"
    # 语言列表，例如 ["chinese", "english"]
    lang: Optional[List[str]] = None
    # 是否强制整页 OCR
    force_full_page_ocr: bool = False
    # 自定义模型路径（RapidOCR 等）
    det_model_path: Optional[str] = None
    rec_model_path: Optional[str] = None
    cls_model_path: Optional[str] = None
    # 其它透传给引擎的选项
    extra_options: Dict[str, Any] = field(default_factory=dict)
