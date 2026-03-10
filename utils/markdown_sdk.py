"""
Markdown SDK 入口（from utils.markdown_sdk import ...）。

在原有 Docling 能力基础上，增加：
- 显式的 OCR 后端切换能力（通过 PdfOcrConfig 或便捷函数参数 ocr_backend）。
- 统一的 MarkdownConverter 抽象，可选择 Docling 或 MinerU 作为底层引擎。
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from core import (
    DocumentToMarkdownConverter,
    docx_to_markdown,
    pdf_to_markdown,
    pptx_to_markdown,
    scanned_pdf_to_markdown,
    xlsx_to_markdown,
)
from models import ImageExportMode, OcrBackend, PdfOcrConfig

import core
import models


class MarkdownEngine(str, Enum):
    """Markdown 转换底层引擎。"""

    DOCLING = "docling"
    MINERU = "mineru"


class _DoclingMarkdownEngine:
    """基于 Docling 的 Markdown 转换实现。"""

    def __init__(
        self,
        pdf_ocr_config: Optional[PdfOcrConfig] = None,
        image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
        show_progress: bool = True,
        do_formula_enrichment: bool = False,
        replace_formula_placeholder: Optional[str] = None,
        fix_misplaced_ampersand_in_formula: bool = True,
        **_: Any,
    ) -> None:
        self._converter = DocumentToMarkdownConverter(
            pdf_ocr_config=pdf_ocr_config,
            image_export_mode=image_export_mode,
            show_progress=show_progress,
            do_formula_enrichment=do_formula_enrichment,
            replace_formula_placeholder=replace_formula_placeholder,
            fix_misplaced_ampersand_in_formula=fix_misplaced_ampersand_in_formula,
        )

    def convert(
        self,
        document_path: Union[str, Path],
        output_filename: str,
        save_dir: Union[str, Path],
        **_: Any,
    ) -> Path:
        return self._converter.convert(document_path, output_filename, save_dir)


class _MineruMarkdownEngine:
    """
    基于 MinerU 的 Markdown 转换实现。

    使用 MinerU 官方 Python 模块（与 README 中的简化示例类似），
    直接走 SDK + VLM 后端，而不是通过命令行。
    """

    def __init__(
        self,
        backend: str = "transformers",
        method: str = "auto",
        lang: str = "ch",
        server_url: Optional[str] = None,
        start_page_id: int = 0,
        end_page_id: Optional[int] = None,
        **_: Any,
    ) -> None:
        # 与 MinerU README / 示例脚本的参数保持一致含义
        self.backend = backend
        self.method = method
        self.lang = lang
        self.server_url = server_url
        self.start_page_id = start_page_id
        self.end_page_id = end_page_id

    def convert(
        self,
        document_path: Union[str, Path],
        output_filename: str,
        save_dir: Union[str, Path],
        **_: Any,
    ) -> Path:
        # 优先使用本地已下载的 VLM，避免再次触发 ModelScope/HF 拉取导致卡在 "Fetching 14 files"
        os.environ.setdefault("MINERU_MODEL_SOURCE", "local")
        try:
            # 参考 MinerU 官方示例脚本，直接使用其 Python 模块
            from mineru.cli.common import (  # type: ignore[import-not-found]
                convert_pdf_bytes_to_bytes_by_pypdfium2,
                prepare_env,
                read_fn,
            )
            from mineru.data.data_reader_writer import FileBasedDataWriter  # type: ignore[import-not-found]
            from mineru.utils.enum_class import MakeMode  # type: ignore[import-not-found]
            from mineru.backend.vlm.vlm_analyze import (  # type: ignore[import-not-found]
                doc_analyze as vlm_doc_analyze,
            )
            from mineru.backend.vlm.vlm_middle_json_mkcontent import (  # type: ignore[import-not-found]
                union_make as vlm_union_make,
            )
        except ImportError as e:  # pragma: no cover - 依赖不满足时由测试/调用侧处理
            raise ImportError("使用 MinerU 引擎需要先安装 mineru 包。") from e

        path = Path(document_path)
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            raise FileNotFoundError(f"MinerU 输入文件不存在: {path}")

        # 对齐 MinerU 官方示例中的参数约定
        backend = self.backend
        if backend.startswith("vlm-"):
            backend = backend[4:]

        # 读取并规范化 PDF 字节
        pdf_bytes = read_fn(str(path))
        pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(
            pdf_bytes,
            self.start_page_id,
            self.end_page_id,
        )

        # 解析方法：这里固定走 VLM 流程（官方示例中将 parse_method 设为 "vlm"）
        parse_method = "vlm"

        # 使用调用者给的输出文件名（去掉扩展名）作为 MinerU 的逻辑文件名
        pdf_file_name = Path(output_filename).stem

        # 准备 MinerU 的输出目录结构：images / markdown / etc.
        local_image_dir, local_md_dir = prepare_env(
            str(save_dir),
            pdf_file_name,
            parse_method,
        )
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)

        # 走 VLM 后端做解析
        middle_json, infer_result = vlm_doc_analyze(
            pdf_bytes,
            image_writer=image_writer,
            backend=backend,
            server_url=self.server_url,
        )

        pdf_info = middle_json["pdf_info"]
        image_dir_name = str(Path(local_image_dir).name)

        # 生成 Markdown 文本（对应官方示例中的 vlm_union_make + MakeMode.MM_MD）
        md_content_str = vlm_union_make(
            pdf_info,
            MakeMode.MM_MD,
            image_dir_name,
        )

        out_name = (
            output_filename if str(output_filename).endswith(".md") else f"{output_filename}.md"
        )
        out_path = Path(local_md_dir) / out_name
        out_path.write_text(md_content_str, encoding="utf-8")
        return out_path


class MarkdownConverter:
    """
    统一 Markdown 转换入口。

    - engine=MarkdownEngine.DOCLING：使用 Docling 作为底层。
    - engine=MarkdownEngine.MINERU：使用 MinerU 作为底层。
    """

    def __init__(
        self,
        engine: MarkdownEngine = MarkdownEngine.DOCLING,
        pdf_ocr_config: Optional[PdfOcrConfig] = None,
        image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
        show_progress: bool = True,
        do_formula_enrichment: bool = False,
        replace_formula_placeholder: Optional[str] = None,
        fix_misplaced_ampersand_in_formula: bool = True,
        **engine_kwargs: Any,
    ) -> None:
        self.engine = engine
        if engine == MarkdownEngine.DOCLING:
            self._impl = _DoclingMarkdownEngine(
                pdf_ocr_config=pdf_ocr_config,
                image_export_mode=image_export_mode,
                show_progress=show_progress,
                do_formula_enrichment=do_formula_enrichment,
                replace_formula_placeholder=replace_formula_placeholder,
                fix_misplaced_ampersand_in_formula=fix_misplaced_ampersand_in_formula,
            )
        elif engine == MarkdownEngine.MINERU:
            self._impl = _MineruMarkdownEngine(**engine_kwargs)
        else:
            raise ValueError(f"未知 Markdown 引擎: {engine}")

    def convert(
        self,
        document_path: Union[str, Path],
        output_filename: str,
        save_dir: Union[str, Path],
        **kwargs: Any,
    ) -> Path:
        """
        将单个文档转换为 Markdown。

        对于 Docling 引擎，额外的 **kwargs 当前会被忽略；
        对于 MinerU 引擎，可用于未来扩展（如模型选择等）。
        """
        return self._impl.convert(document_path, output_filename, save_dir, **kwargs)


__all__ = [
    "DocumentToMarkdownConverter",
    "ImageExportMode",
    "OcrBackend",
    "PdfOcrConfig",
    "pdf_to_markdown",
    "scanned_pdf_to_markdown",
    "docx_to_markdown",
    "pptx_to_markdown",
    "xlsx_to_markdown",
    "MarkdownEngine",
    "MarkdownConverter",
    "core",
    "models",
]

__version__ = "0.1.0"
