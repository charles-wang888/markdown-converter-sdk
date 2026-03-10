"""
统一文档转 Markdown 工具类：入参为文档路径、输出文件名、保存目录；
支持按 MIME 自动选择转换方式，PDF 支持可配置 OCR；
支持 tqdm 进度条显示转换进度。
"""

import re
from pathlib import Path
from typing import List, Optional, Union

from models import ImageExportMode, OcrBackend, PdfOcrConfig
from utils import detect_mime_from_path, is_supported_mime

# docling 图片导出模式（REFERENCED=外部队列引用，EMBEDDED=Base64 内嵌）
try:
    from docling_core.types.doc import ImageRefMode as _ImageRefMode
except ImportError:
    try:
        from docling.types.doc import ImageRefMode as _ImageRefMode
    except ImportError:
        _ImageRefMode = None

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def _build_pdf_pipeline_options(
    ocr_config: Optional[PdfOcrConfig] = None,
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
    do_formula_enrichment: bool = False,
):
    """根据 PdfOcrConfig 与图片导出模式构建 docling PdfPipelineOptions。"""
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        OcrAutoOptions,
        OcrMacOptions,
        PdfPipelineOptions,
        RapidOcrOptions,
        TesseractCliOcrOptions,
        TesseractOcrOptions,
    )

    do_ocr = True
    ocr_options = OcrAutoOptions()

    if ocr_config is not None:
        do_ocr = ocr_config.do_ocr
        lang = ocr_config.lang or ["chinese", "english"]
        extra = ocr_config.extra_options or {}

        if ocr_config.backend == OcrBackend.AUTO:
            ocr_options = OcrAutoOptions()
        elif ocr_config.backend in (OcrBackend.RAPID_OCR, OcrBackend.PADDLE_OCR):
            backend = "paddle" if ocr_config.backend == OcrBackend.PADDLE_OCR else ocr_config.rapid_ocr_backend
            ocr_options = RapidOcrOptions(
                lang=lang,
                force_full_page_ocr=ocr_config.force_full_page_ocr,
                backend=backend,
                det_model_path=ocr_config.det_model_path,
                rec_model_path=ocr_config.rec_model_path,
                cls_model_path=ocr_config.cls_model_path,
                rapidocr_params=extra,
            )
        elif ocr_config.backend == OcrBackend.EASY_OCR:
            ocr_options = EasyOcrOptions(lang=lang, force_full_page_ocr=ocr_config.force_full_page_ocr)
        elif ocr_config.backend == OcrBackend.TESSERACT:
            ocr_options = TesseractOcrOptions(lang=lang, force_full_page_ocr=ocr_config.force_full_page_ocr)
        elif ocr_config.backend == OcrBackend.TESSERACT_CLI:
            ocr_options = TesseractCliOcrOptions(lang=lang, force_full_page_ocr=ocr_config.force_full_page_ocr)
        elif ocr_config.backend == OcrBackend.OCR_MAC:
            ocr_options = OcrMacOptions(lang=lang or ["en-US"], force_full_page_ocr=ocr_config.force_full_page_ocr)
        elif ocr_config.backend in (OcrBackend.MINER_U, OcrBackend.DEEPSEEK_OCR):
            # 暂无内置，使用 RapidOCR 作为默认
            ocr_options = RapidOcrOptions(
                lang=lang,
                force_full_page_ocr=ocr_config.force_full_page_ocr,
                backend=ocr_config.rapid_ocr_backend,
            )

    # 构造时传入 do_formula_enrichment，确保管道会执行公式增强（对应 CLI --enrich-formula）
    try:
        pipeline_options = PdfPipelineOptions(
            do_ocr=do_ocr,
            ocr_options=ocr_options,
            do_formula_enrichment=do_formula_enrichment,
        )
    except TypeError:
        # 旧版 Docling 可能无此参数，则先构造再按属性设置
        pipeline_options = PdfPipelineOptions(do_ocr=do_ocr, ocr_options=ocr_options)
        if do_formula_enrichment and hasattr(pipeline_options, "do_formula_enrichment"):
            pipeline_options.do_formula_enrichment = True
    # 当需要导出图片（referenced/embedded）时启用文档内图片生成，以便写入 MD 或 artifacts
    if image_export_mode in (ImageExportMode.REFERENCED, ImageExportMode.EMBEDDED):
        pipeline_options.generate_picture_images = True
    return pipeline_options


def _get_document_converter(
    pdf_ocr_config: Optional[PdfOcrConfig] = None,
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
    do_formula_enrichment: bool = False,
):
    """构建 DocumentConverter，PDF 使用可配置的 OCR、图片导出与可选公式增强。"""
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = _build_pdf_pipeline_options(
        pdf_ocr_config, image_export_mode, do_formula_enrichment
    )

    # 公式增强必须使用 Parse 后端 + StandardPdfPipeline，否则仍会输出 formula-not-decoded（见 docling#1029）
    pdf_backend = None
    standard_pipeline = None
    if do_formula_enrichment:
        try:
            from docling.document_converter import StandardPdfPipeline as _StdPipeline
            standard_pipeline = _StdPipeline
            # 优先 V4，其次 V2（不同 docling 版本导出名不同）
            for name in ("DoclingParseV4DocumentBackend", "DoclingParseV2DocumentBackend"):
                try:
                    from docling import document_converter as _dc
                    pdf_backend = getattr(_dc, name, None)
                    if pdf_backend is not None:
                        break
                except Exception:
                    pass
            if pdf_backend is None:
                try:
                    from docling.backend.docling_parse_backend import (
                        DoclingParseV2DocumentBackend,
                    )
                    pdf_backend = DoclingParseV2DocumentBackend
                except ImportError:
                    pass
        except ImportError:
            pass
    if do_formula_enrichment and pdf_backend is not None and standard_pipeline is not None:
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    backend=pdf_backend,
                    pipeline_cls=standard_pipeline,
                    pipeline_options=pipeline_options,
                ),
            },
        )

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        },
    )


class _ProgressContext:
    """单步进度条上下文：进入时显示 0%，退出时更新为 100%。无 tqdm 时为空操作。"""

    def __init__(self, show: bool, desc: str = "转换中", unit: str = "doc"):
        self.show = show and (tqdm is not None)
        self.desc = desc
        self.unit = unit
        self._pbar = None

    def __enter__(self):
        if self.show:
            self._pbar = tqdm(total=1, desc=self.desc, unit=self.unit)
        return self

    def __exit__(self, *args):
        if self._pbar is not None:
            self._pbar.update(1)
            self._pbar.close()
        return False


def _resolve_image_ref_mode(mode: ImageExportMode):
    """将 SDK 的 ImageExportMode 转为 docling 的 ImageRefMode；不支持时返回 None。"""
    if _ImageRefMode is None:
        return None
    return _ImageRefMode.REFERENCED if mode == ImageExportMode.REFERENCED else _ImageRefMode.EMBEDDED


class DocumentToMarkdownConverter:
    """
    文档转 Markdown 工具类。
    - 入参：文档路径、转换后文件名、保存目录。
    - 支持根据 MIME 自动选择转换方式。
    - PDF 支持可配置 OCR（如 RapidOCR、EasyOCR、Tesseract、Paddle 等）。
    - 支持 tqdm 进度条显示转换进度。
    - 支持文档内嵌图片导出方式：referenced（外部队列引用，默认）或 embedded（Base64 内嵌）。

    关于「公式/段落跑错小节」：
    导出内容的小节顺序与公式归属由 Docling 的阅读顺序（reading order）决定，其布局模型
    根据版面位置（多栏、图混排、公式与代码块相邻等）推断顺序。复杂版面下，公式可能被
    归到相邻小节（如公式块下的公式出现在代码块小节后）。这是上游行为，详见：
    https://github.com/docling-project/docling/issues/570
    通用做法：升级 Docling、或向 Docling 提供问题 PDF 以改进阅读顺序模型；本 SDK 不做
    针对单篇文档的段落移动，以免破坏其它文档。
    """

    # Docling 未识别公式时在 MD 中留下的占位注释
    FORMULA_NOT_DECODED_PLACEHOLDER = "<!-- formula-not-decoded -->"

    @staticmethod
    def _fix_misplaced_ampersand_in_display_math(text: str) -> str:
        """在 $$...$$ 块内将「 = & 」改为「 = 」，避免 Misplaced & 渲染错误（来自 align 导出为单行时）。"""
        def replace_in_block(m: re.Match) -> str:
            block = m.group(1)
            block = block.replace(" = & ", " = ")
            return "$$" + block + "$$"
        return re.sub(r"\$\$([^$]+)\$\$", replace_in_block, text)

    def __init__(
        self,
        pdf_ocr_config: Optional[PdfOcrConfig] = None,
        show_progress: bool = True,
        image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
        do_formula_enrichment: bool = False,
        replace_formula_placeholder: Optional[str] = None,
        fix_misplaced_ampersand_in_formula: bool = True,
    ):
        """
        :param pdf_ocr_config: PDF 的 OCR 配置；为 None 时使用默认（启用 OCR，自动选择引擎）。
        :param show_progress: 是否在转换时显示 tqdm 进度条；默认 True。
        :param image_export_mode: 内嵌图片导出方式：REFERENCED（生成 artifacts 目录并引用，默认）或 EMBEDDED（Base64 内嵌）。
        :param do_formula_enrichment: 是否启用 Docling 公式增强（提取 LaTeX，对应 CLI --enrich-formula）；默认 False。仅对 PDF 生效，DOCX/PPTX/XLSX 不受此参数影响。
        :param replace_formula_placeholder: 写入 MD 后，将「<!-- formula-not-decoded -->」替换为该字符串；None 不替换，"" 表示删除。
        :param fix_misplaced_ampersand_in_formula: 是否在 $$...$$ 块内将「 = & 」改为「 = 」以修复 Misplaced &；默认 True。
        """
        self._pdf_ocr_config = pdf_ocr_config
        self._image_export_mode = image_export_mode
        self._replace_formula_placeholder = replace_formula_placeholder
        self._fix_misplaced_ampersand_in_formula = fix_misplaced_ampersand_in_formula
        self._converter = _get_document_converter(
            pdf_ocr_config, image_export_mode, do_formula_enrichment
        )
        self._show_progress = show_progress

    def convert(
        self,
        document_path: Union[str, Path],
        output_filename: str,
        save_dir: Union[str, Path],
        show_progress: Optional[bool] = None,
    ) -> Path:
        """
        将单个文档转为 Markdown 并写入指定目录。

        :param document_path: 源文档路径（PDF/DOCX/PPTX/XLSX）
        :param output_filename: 输出文件名（建议带 .md，否则自动补全）
        :param save_dir: 保存目录，不存在则会创建
        :param show_progress: 是否显示进度条；None 时使用构造时的 show_progress
        :return: 写入的 Markdown 文件路径
        """
        path = Path(document_path)
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        use_progress = show_progress if show_progress is not None else self._show_progress
        out_name = output_filename if output_filename.endswith(".md") else f"{output_filename}.md"
        out_path = save_dir / out_name

        with _ProgressContext(use_progress, desc=f"转换 {path.name}", unit="doc"):
            mime, _ = detect_mime_from_path(path)
            if not is_supported_mime(mime):
                raise ValueError(f"不支持的文档类型: {mime}，仅支持 PDF/DOCX/PPTX/XLSX")

            result = self._converter.convert(str(path))
            image_ref_mode = _resolve_image_ref_mode(self._image_export_mode)
            if image_ref_mode is not None and hasattr(result.document, "save_as_markdown"):
                # 显式创建并传入 artifacts_dir，避免 docling 在部分环境下未正确创建导致 FileNotFoundError
                out_path_resolved = Path(out_path).resolve()
                artifacts_dir = out_path_resolved.parent / f"{out_path_resolved.stem}_artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                result.document.save_as_markdown(
                    str(out_path_resolved),
                    artifacts_dir=artifacts_dir,
                    image_mode=image_ref_mode,
                )
            else:
                markdown_content = result.document.export_to_markdown()
                out_path.write_text(markdown_content, encoding="utf-8")
        if self._replace_formula_placeholder is not None or self._fix_misplaced_ampersand_in_formula:
            text = out_path.read_text(encoding="utf-8")
            if self._replace_formula_placeholder is not None:
                text = text.replace(
                    DocumentToMarkdownConverter.FORMULA_NOT_DECODED_PLACEHOLDER,
                    self._replace_formula_placeholder,
                )
            if self._fix_misplaced_ampersand_in_formula:
                text = DocumentToMarkdownConverter._fix_misplaced_ampersand_in_display_math(text)
            out_path.write_text(text, encoding="utf-8")
        return out_path

    def convert_by_mime(
        self,
        document_path: Union[str, Path],
        output_filename: str,
        save_dir: Union[str, Path],
        mime_type: Optional[str] = None,
        show_progress: Optional[bool] = None,
    ) -> Path:
        """
        与 convert 行为一致；若提供 mime_type 则不再检测，直接按该 MIME 用 docling 转换。
        用于已知 MIME 时避免重复读文件。
        """
        path = Path(document_path)
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        use_progress = show_progress if show_progress is not None else self._show_progress
        out_name = output_filename if output_filename.endswith(".md") else f"{output_filename}.md"
        out_path = save_dir / out_name

        with _ProgressContext(use_progress, desc=f"转换 {path.name}", unit="doc"):
            mime = mime_type or detect_mime_from_path(path)[0]
            if not is_supported_mime(mime):
                raise ValueError(f"不支持的文档类型: {mime}")

            result = self._converter.convert(str(path))
            image_ref_mode = _resolve_image_ref_mode(self._image_export_mode)
            if image_ref_mode is not None and hasattr(result.document, "save_as_markdown"):
                out_path_resolved = Path(out_path).resolve()
                artifacts_dir = out_path_resolved.parent / f"{out_path_resolved.stem}_artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                result.document.save_as_markdown(
                    str(out_path_resolved),
                    artifacts_dir=artifacts_dir,
                    image_mode=image_ref_mode,
                )
            else:
                markdown_content = result.document.export_to_markdown()
                out_path.write_text(markdown_content, encoding="utf-8")
        if self._replace_formula_placeholder is not None or self._fix_misplaced_ampersand_in_formula:
            text = out_path.read_text(encoding="utf-8")
            if self._replace_formula_placeholder is not None:
                text = text.replace(
                    DocumentToMarkdownConverter.FORMULA_NOT_DECODED_PLACEHOLDER,
                    self._replace_formula_placeholder,
                )
            if self._fix_misplaced_ampersand_in_formula:
                text = DocumentToMarkdownConverter._fix_misplaced_ampersand_in_display_math(text)
            out_path.write_text(text, encoding="utf-8")
        return out_path

    def convert_all(
        self,
        document_paths: List[Union[str, Path]],
        save_dir: Union[str, Path],
        output_filenames: Optional[List[str]] = None,
        show_progress: Optional[bool] = None,
    ) -> List[Path]:
        """
        批量将多个文档转为 Markdown，并显示整体进度条。

        :param document_paths: 源文档路径列表
        :param save_dir: 保存目录
        :param output_filenames: 各文件对应的输出文件名（不含路径）；为 None 时使用源文件名
        :param show_progress: 是否显示 tqdm 进度条；None 时使用构造时的 show_progress
        :return: 各文档对应的输出 .md 路径列表
        """
        paths = [Path(p) for p in document_paths]
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        names = output_filenames if output_filenames is not None else [p.stem for p in paths]
        if len(names) != len(paths):
            raise ValueError("output_filenames 长度须与 document_paths 一致")

        use_progress = show_progress if show_progress is not None else self._show_progress
        iterator = paths
        if use_progress and tqdm is not None:
            iterator = tqdm(paths, desc="批量转换", unit="doc")

        out_paths = []
        for i, path in enumerate(iterator):
            out_paths.append(self.convert(path, names[i], save_dir, show_progress=False))
        return out_paths


# 便捷函数：常规 PDF -> MD（不强制 OCR）
def pdf_to_markdown(
    document_path: Union[str, Path],
    output_filename: str,
    save_dir: Union[str, Path],
    use_ocr: bool = False,
    ocr_backend: Optional[OcrBackend] = None,
    ocr_config: Optional[PdfOcrConfig] = None,
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
) -> Path:
    """
    常规 PDF 转 Markdown。

    - use_ocr=False 且未显式传入 ocr_config 时，依赖 PDF 内嵌文本，不启用 OCR。
    - 传入 ocr_backend 可在不自建 PdfOcrConfig 的情况下快速切换底层 OCR 引擎。
    - 若提供 ocr_config，则优先使用该配置，忽略 use_ocr / ocr_backend。
    """
    if ocr_config is not None:
        config = ocr_config
    else:
        backend = ocr_backend if ocr_backend is not None else OcrBackend.RAPID_OCR
        config = PdfOcrConfig(do_ocr=use_ocr, backend=backend)
    c = DocumentToMarkdownConverter(pdf_ocr_config=config, image_export_mode=image_export_mode)
    return c.convert(document_path, output_filename, save_dir)


# 便捷函数：扫描版 PDF -> MD（启用 OCR）
def scanned_pdf_to_markdown(
    document_path: Union[str, Path],
    output_filename: str,
    save_dir: Union[str, Path],
    ocr_backend: Optional[OcrBackend] = None,
    ocr_config: Optional[PdfOcrConfig] = None,
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
) -> Path:
    """
    扫描版 PDF 转 Markdown，默认启用 OCR。

    - 默认使用 RapidOCR（OcrBackend.RAPID_OCR）。
    - 传入 ocr_backend 可快速切换为 PaddleOCR、Tesseract 等后端。
    - 若提供 ocr_config，则优先使用该配置，忽略 ocr_backend。
    """
    if ocr_config is not None:
        config = ocr_config
    else:
        backend = ocr_backend if ocr_backend is not None else OcrBackend.RAPID_OCR
        config = PdfOcrConfig(do_ocr=True, backend=backend)
    c = DocumentToMarkdownConverter(pdf_ocr_config=config, image_export_mode=image_export_mode)
    return c.convert(document_path, output_filename, save_dir)


def docx_to_markdown(
    document_path: Union[str, Path],
    output_filename: str,
    save_dir: Union[str, Path],
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
) -> Path:
    """DOCX 转 Markdown。"""
    c = DocumentToMarkdownConverter(image_export_mode=image_export_mode)
    return c.convert(document_path, output_filename, save_dir)


def pptx_to_markdown(
    document_path: Union[str, Path],
    output_filename: str,
    save_dir: Union[str, Path],
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
) -> Path:
    """PPTX 转 Markdown。"""
    c = DocumentToMarkdownConverter(image_export_mode=image_export_mode)
    return c.convert(document_path, output_filename, save_dir)


def xlsx_to_markdown(
    document_path: Union[str, Path],
    output_filename: str,
    save_dir: Union[str, Path],
    image_export_mode: ImageExportMode = ImageExportMode.REFERENCED,
) -> Path:
    """XLSX 转 Markdown。"""
    c = DocumentToMarkdownConverter(image_export_mode=image_export_mode)
    return c.convert(document_path, output_filename, save_dir)
