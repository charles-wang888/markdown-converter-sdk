"""简单示例：使用 docling-sdk 将单个文件转为 Markdown（直接在代码中配置“参数”）。

建议打开本文件阅读其中的常量与调用方式，然后按需修改路径与配置。
每个测试用例运行时会生成同名执行日志，如 scanpdf_run_markdown_converter_with_docling.log。
"""

import sys
from datetime import datetime
from pathlib import Path

from utils.markdown_sdk import (
    MarkdownConverter,
    MarkdownEngine,
    OcrBackend,
    PdfOcrConfig,
)

# 执行日志目录：tests/logs（与 main.py 同目录下的 tests 子目录内）
_LOG_DIR = Path(__file__).resolve().parent / "tests" / "logs"


def _run_one_test(func):
    """运行单个测试用例，将 stdout 同时写入 tests/logs/{方法名}.log 并保留控制台输出。
    作为顶层函数便于 multiprocessing 序列化，并行时由子进程调用。"""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOG_DIR / f"{func.__name__}.log"
    orig_stdout = sys.stdout
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            class Tee:
                def write(self, data):
                    orig_stdout.write(data)
                    f.write(data)
                def flush(self):
                    orig_stdout.flush()
                    f.flush()
            sys.stdout = Tee()
            f.write(f"=== {func.__name__} 执行开始 {datetime.now().isoformat()} ===\n")
            f.flush()
            result = func()
            f.write(f"=== {func.__name__} 执行结束 {datetime.now().isoformat()} ===\n")
            return result
    finally:
        sys.stdout = orig_stdout


def scanpdf_run_markdown_converter_with_docling() -> Path:
    """扫描 PDF 用例：对扫描版 PDF 做 OCR 后转 Markdown。

    通过 MarkdownConverter + Docling 引擎，对 工程分享-扫描型.pdf 做 OCR 后输出 Markdown。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = PdfOcrConfig(do_ocr=True, backend=OcrBackend.RAPID_OCR)
    converter = MarkdownConverter(
        engine=MarkdownEngine.DOCLING,
        pdf_ocr_config=cfg,
    )
    out_path = converter.convert(
        Path("tests/raw_file/工程分享-扫描型.pdf"),
        "工程分享-扫描型.pdf.md",
        out_dir,
    )
    print(f"[工程分享-扫描型.pdf] Markdown 已生成: {out_path.resolve()}")
    return out_path


def normalpdf_run_markdown_converter_with_docling_withLaTex() -> Path:
    """常规 PDF 用例：转 Markdown（含 LaTeX 公式与代码片段）。

    通过 MarkdownConverter + Docling 引擎，输入 测试文档_包含LaTex公式以及代码片段.pdf，不启用 OCR，
    启用公式增强（--enrich-formula）以支持 LaTeX 公式渲染。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = PdfOcrConfig(do_ocr=False)
    converter = MarkdownConverter(
        engine=MarkdownEngine.DOCLING,
        pdf_ocr_config=cfg,
        do_formula_enrichment=True,   #如果文档中没有LaTex公式就不要这个选项
    )
    out_path = converter.convert(
        Path("tests/raw_file/测试文档_包含LaTex公式以及代码片段.pdf"),
        "测试文档_包含LaTex公式以及代码片段.pdf.md",
        out_dir,
    )
    print(f"[测试文档_包含LaTex公式以及代码片段.pdf] Markdown 已生成: {out_path.resolve()}")
    return out_path


def normalpdf_run_markdown_converter_with_docling_withoutLaTex() -> Path:
    """常规 PDF 用例：转 Markdown

    通过 MarkdownConverter + Docling 引擎，不启用 OCR，不启用公式增强（--enrich-formula）

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = PdfOcrConfig(do_ocr=False)
    converter = MarkdownConverter(
        engine=MarkdownEngine.DOCLING,
        pdf_ocr_config=cfg
    )
    out_path = converter.convert(
        Path("tests/raw_file/匿名双盲政策.pdf"),
        "匿名双盲政策.pdf.md",
        out_dir,
    )
    print(f"[匿名双盲政策.pdf] Markdown 已生成: {out_path.resolve()}")
    return out_path


def excel_run_markdown_converter_with_docling() -> Path:
    """Excel 用例：将 XLSX 转为 Markdown。

    通过 MarkdownConverter + Docling 引擎，输入 测试文档_包含LaTex公式以及代码片段.xlsx。

    说明：Docling 的 do_formula_enrichment（LaTeX 公式提取）仅对 PDF 生效；XLSX 使用默认
    Excel 解析，单元格中的 LaTeX 会以纯文本导出，无法被识别为公式。若需在 MD 中正确渲染
    公式，可先将该 Sheet 导出为 PDF，再用 normalpdf_run_markdown_converter_with_docling_withLaTex
    的方式转换（do_formula_enrichment=True）。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
    out_path = converter.convert(
        Path("tests/raw_file/测试文档_包含LaTex公式以及代码片段.xlsx"),
        "测试文档_包含LaTex公式以及代码片段.xlsx.md",
        out_dir,
    )
    print(f"[测试文档_包含LaTex公式以及代码片段.xlsx] Markdown 已生成: {out_path.resolve()}")
    return out_path


def word_run_markdown_converter_with_docling_without_LaTex() -> Path:
    """Word 用例：将 DOCX（匿名双盲政策.docx）转为 Markdown。

    通过 MarkdownConverter + Docling 引擎，输入 匿名双盲政策.docx。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
    out_path = converter.convert(
        Path("tests/raw_file/匿名双盲政策.docx"),
        "匿名双盲政策.docx.md",
        out_dir,
    )
    print(f"[匿名双盲政策.docx] Markdown 已生成: {out_path.resolve()}")
    return out_path


def word_run_markdown_converter_with_docling_with_LaTex() -> Path:
    """Word 用例：将包含LaTex公式的Word文件转为 Markdown。

    通过 MarkdownConverter + Docling 引擎，输入 测试文档_复杂中式报表表格.docx。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
    out_path = converter.convert(
        Path("tests/raw_file/测试文档_包含LaTex公式以及代码片段.docx"),
        "测试文档_包含LaTex公式以及代码片段.docx.md",
        out_dir,
    )
    print(f"[测试文档_包含LaTex公式以及代码片段.docx] Markdown 已生成: {out_path.resolve()}")
    return out_path


def ppt_run_markdown_converter_with_docling() -> Path:
    """PPT 用例：将 PPTX 转为 Markdown。

    通过 MarkdownConverter + Docling 引擎，输入  端午节.pptx。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
    out_path = converter.convert(
        Path("tests/raw_file/端午节.pptx"),
        "端午节.pptx.md",
        out_dir,
    )
    print(f"[端午节.pptx] Markdown 已生成: {out_path.resolve()}")
    return out_path


def scanpdf_run_markdown_converter_with_mineru() -> Path:
    """MinerU 用例：使用 MinerU 引擎将 PDF 转为 Markdown。

    通过 MarkdownConverter + MinerU 引擎，输入 工程分享-扫描型.pdf。
    需要先安装 mineru 包，并已下载 VLM 模型（如 MINERU_MODEL_SOURCE=local）。

    Returns:
        Path: 生成的 .md 文件路径。
    """
    out_dir = Path("tests/raw_file_output")
    out_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkdownConverter(engine=MarkdownEngine.MINERU)
    out_path = converter.convert(
        Path("tests/raw_file/工程分享-扫描型.pdf"),
        "工程分享-扫描型-mineru方式运行.pdf.md",
        out_dir,
    )
    print(f"[工程分享-扫描型-mineru方式运行.pdf] Markdown 已生成: {out_path.resolve()}")
    return out_path


# 全部测试用例（用于并行运行）
TEST_CASES = [
    scanpdf_run_markdown_converter_with_docling,
    normalpdf_run_markdown_converter_with_docling_withLaTex,
    normalpdf_run_markdown_converter_with_docling_withoutLaTex,
    excel_run_markdown_converter_with_docling,
    word_run_markdown_converter_with_docling_without_LaTex,
    word_run_markdown_converter_with_docling_with_LaTex,
    ppt_run_markdown_converter_with_docling,
    scanpdf_run_markdown_converter_with_mineru
]


def run_all_tests_parallel(max_workers: int = 4) -> None:
    """并行运行全部测试用例，日志写入 tests/logs/{方法名}.log。"""
    import concurrent.futures
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"并行运行 {len(TEST_CASES)} 个用例，日志目录: {_LOG_DIR.resolve()}")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_one_test, tc): tc.__name__ for tc in TEST_CASES}
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            try:
                path = fut.result()
                print(f"[OK] {name} -> {path}")
            except Exception as e:
                print(f"[FAIL] {name}: {e}")
    print("全部用例执行完毕。")


if __name__ == "__main__":
    # 方式一：串行，按需取消注释要跑的用例（会写日志到 tests/logs/{方法名}.log）
    # _run_one_test(scanpdf_run_markdown_converter_with_docling)
    # _run_one_test(normalpdf_run_markdown_converter_with_docling_withLaTex)
    # _run_one_test(normalpdf_run_markdown_converter_with_docling_withoutLaTex)
    # _run_one_test(excel_run_markdown_converter_with_docling)
    # _run_one_test(word_run_markdown_converter_with_docling_without_LaTex)
    # _run_one_test(word_run_markdown_converter_with_docling_with_LaTex)
    # _run_one_test(ppt_run_markdown_converter_with_docling)
    # _run_one_test(scanpdf_run_markdown_converter_with_mineru)

    # 方式二：并行运行全部用例（取消下一行注释）
    run_all_tests_parallel()
