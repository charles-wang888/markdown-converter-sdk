# MarkDown Converter SDK

提供 **Docling** 与 **MinerU** 统一入口的 Python SDK，实现各类文档转 Markdown 的统一样式接口，支持按 MIME 自动识别、可配置 PDF OCR，并可切换 Docling / MinerU 引擎。

## 背景

- **Docling**：在各类对比与实测中，是开源框架里**文档转 Markdown 效果最好**的一类方案，适合作为通用文档转 MD 的默认引擎。相关实验与评测可参考：
  - [知乎：Docling 相关实验组（一）](https://zhuanlan.zhihu.com/p/2013520612556055422)
  - [知乎：Docling 相关实验组（二）](https://zhuanlan.zhihu.com/p/2013522452911772874)
  - [知乎：Docling 相关实验组（三）](https://zhuanlan.zhihu.com/p/2013536546335261017)
  - [知乎：Docling 相关实验组（四）](https://zhuanlan.zhihu.com/p/2013545016845415123)
  - [知乎：Docling 相关实验组（五）](https://zhuanlan.zhihu.com/p/2013550937835349009)
  - [知乎：Docling 相关实验组（六）](https://zhuanlan.zhihu.com/p/2013555748265809887)
  - [知乎：Docling 相关实验组（七）](https://zhuanlan.zhihu.com/p/2013560775533404414)
  - [知乎：Docling 相关实验组（八）](https://zhuanlan.zhihu.com/p/2013581193015222573)

- **MinerU**：在 **PDF 精细化处理**（尤其是**扫描版 PDF**）上效果突出，适合对版面、表格、公式、多栏排版要求高的场景。
  - **文档级精度**（OmniDocBench v1.5 End-to-End）：约 **82%+**（pipeline 后端，速度快、无幻觉、基于 transformers）或 **90%+**（VLM 后端，精度更高、速度较慢）。
  - **综合准确率**（第三方实测，如 53AI）：约 **92%–95%**。
  - **优势**：干扰信息过滤好，在网页/复杂版式下比 PaddleOCR 约高 3%–5%。
  - **劣势**：高分辨率扫描件中文字模糊处易错，比 DeepSeek-OCR 约低 2%–3%。
  - **适用场景**：中文科技文献、多栏排版、表格、公式、页眉页脚剔除、版面还原。

本 SDK 将 **Docling** 与 **MinerU** 结合，提供**统一使用入口**与工具，把各类文档（PDF、DOCX、PPTX、XLSX 等）转化为 Markdown，从而满足 **Spec Coding** 中「万事万物皆 Markdown」的诉求。

## 项目结构

```
markdown-converter-sdk/
├── core/                     # 核心转换逻辑（项目根直接子目录）
│   ├── __init__.py
│   └── converter.py
├── models/                   # 配置与数据模型
│   ├── __init__.py
│   └── options.py
├── utils/                    # 工具与 Markdown SDK
│   ├── __init__.py
│   ├── mime.py
│   └── markdown_sdk.py       # Markdown SDK 入口，from utils.markdown_sdk import ...
├── tests/
│   ├── raw_file/             # 真实文档输入
│   ├── raw_file_output/      # 转换结果（每文件一子目录）
│   └── logs/                 # main.py 各用例执行日志（{方法名}.log）
├── main.py                   # 示例与可运行用例（串行/并行）
├── pyproject.toml
└── README.md
```

## 功能概览

- **格式支持**：常规 PDF、扫描版 PDF、DOCX、PPTX、XLSX → Markdown
- **MIME 自动识别**：根据文件内容或扩展名自动选择转换方式
- **入参约定**：文档路径、转换后文件名、保存目录
- **可配置 PDF OCR**：RapidOCR、EasyOCR、Tesseract、Paddle（RapidOCR 的 paddle 后端）、macOS 原生 OCR、自动选择等；预留 MinerU / Deepseek-OCR
- **底层 OCR 可切换**：既可以通过 `PdfOcrConfig` 精细配置，也可以在便捷函数中通过 `ocr_backend` 参数一行切换
- **综合 Markdown 引擎**：统一的 `MarkdownConverter`，支持选择 Docling 或 MinerU 作为底层引擎
- **tqdm 进度条**：单文件转换与批量转换均可显示进度
- **文档内嵌图片导出**：`referenced`（默认）生成 `xxx_artifacts` 目录并写入相对路径引用；`embedded` 将图片以 Base64 内嵌到 MD（不推荐）

---

## 各类型文件转 Markdown（与 main.py 场景对应）

以下场景与项目根目录 `main.py` 中的用例一一对应，可直接在代码中复用或运行 `python main.py` 做试验。

| 场景 | 格式 | 要点 | main.py 对应函数 |
|------|------|------|------------------|
| 扫描版 PDF | PDF | 启用 OCR（如 RapidOCR） | `scanpdf_run_markdown_converter_with_docling` |
| 常规 PDF（含 LaTeX 公式） | PDF | 不 OCR，**启用 `do_formula_enrichment=True`** | `normalpdf_run_markdown_converter_with_docling_withLaTex` |
| 常规 PDF（无公式） | PDF | 不 OCR，不启用公式增强 | `normalpdf_run_markdown_converter_with_docling_withoutLaTex` |
| Excel 表格 | XLSX | 直接转 MD；**公式见下方说明** | `excel_run_markdown_converter_with_docling` |
| Word（无 LaTeX） | DOCX | 普通 DOCX 转 MD | `word_run_markdown_converter_with_docling_without_LaTex` |
| Word（含 LaTeX） | DOCX | 含公式的 DOCX 转 MD | `word_run_markdown_converter_with_docling_with_LaTex` |
| PPT 演示稿 | PPTX | PPTX 转 MD | `ppt_run_markdown_converter_with_docling` |
| MinerU 引擎 | PDF | 使用 MinerU 作为底层引擎（需安装 mineru） | `scanpdf_run_markdown_converter_with_mineru` |

### 代码示例（按场景）

```python
from pathlib import Path
from utils.markdown_sdk import MarkdownConverter, MarkdownEngine, OcrBackend, PdfOcrConfig

out_dir = Path("tests/raw_file_output")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. 扫描 PDF：启用 OCR
cfg = PdfOcrConfig(do_ocr=True, backend=OcrBackend.RAPID_OCR)
converter = MarkdownConverter(engine=MarkdownEngine.DOCLING, pdf_ocr_config=cfg)
converter.convert(Path("tests/raw_file/工程分享-扫描型.pdf"), "工程分享-扫描型.pdf.md", out_dir)

# 2. 常规 PDF + LaTeX 公式：必须 do_formula_enrichment=True（仅对 PDF 生效）
cfg = PdfOcrConfig(do_ocr=False)
converter = MarkdownConverter(engine=MarkdownEngine.DOCLING, pdf_ocr_config=cfg, do_formula_enrichment=True)
converter.convert(Path("tests/raw_file/测试文档_包含LaTex公式以及代码片段.pdf"), "out.md", out_dir)

# 3. 常规 PDF、无公式
converter = MarkdownConverter(engine=MarkdownEngine.DOCLING, pdf_ocr_config=PdfOcrConfig(do_ocr=False))
converter.convert(Path("tests/raw_file/考勤模块-需求文档.pdf"), "out.md", out_dir)

# 4. Excel：表格转 MD（单元格内 LaTeX 不会被识别为公式，见下方「Excel 与 LaTeX」说明）
converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
converter.convert(Path("tests/raw_file/xxx.xlsx"), "out.md", out_dir)

# 5. Word / PPT
converter = MarkdownConverter(engine=MarkdownEngine.DOCLING)
converter.convert(Path("tests/raw_file/xxx.docx"), "out.md", out_dir)
converter.convert(Path("tests/raw_file/xxx.pptx"), "out.md", out_dir)

# 6. MinerU 引擎
converter = MarkdownConverter(engine=MarkdownEngine.MINERU)
converter.convert(Path("tests/raw_file/工程分享-扫描型.pdf"), "out.md", out_dir)
```

---

### 重要：Excel 与 LaTeX 公式

**Docling 对 Excel（XLSX）中的 LaTeX 公式默认不支持。** 公式增强（`do_formula_enrichment`）仅作用于 **PDF 管道**，XLSX 走的是默认 Excel 解析，单元格中的 LaTeX 会以**纯文本**导出，无法被识别为公式并在 Markdown 中正确渲染。

若需要正确识别并渲染 Excel 中的 LaTeX 公式，请：

1. **先将 Excel 内容转为其他格式**（推荐 **PDF**）：在 Excel 中打印/导出为 PDF，或仅将含公式的 Sheet 导出为 PDF。
2. 再使用本 SDK 的 **PDF 转换**，并设置 **`do_formula_enrichment=True`**（参见上文「常规 PDF（含 LaTeX 公式）」场景）。

这样由 PDF 转出的 Markdown 中，公式会被正确提取为 LaTeX 并渲染。DOCX、PPTX 的公式支持以 Docling 当前行为为准；**仅 Excel 明确不支持公式增强，需经 PDF（或其他支持公式的格式）中转。**

---

## 安装

```bash
pip install -e .
```

## 使用

### 统一工具类（推荐）

```python
from pathlib import Path
from utils.markdown_sdk import DocumentToMarkdownConverter, ImageExportMode, PdfOcrConfig, OcrBackend

# 默认：按文件类型自动转换，PDF 使用默认 OCR
converter = DocumentToMarkdownConverter()
out_path = converter.convert(
    document_path="/path/to/document.pdf",
    output_filename="output",
    save_dir="/path/to/output_dir",
)
# 输出文件为 /path/to/output_dir/output.md

# 扫描版 PDF：启用 RapidOCR
ocr_config = PdfOcrConfig(do_ocr=True, backend=OcrBackend.RAPID_OCR)
converter = DocumentToMarkdownConverter(pdf_ocr_config=ocr_config)
out_path = converter.convert("scanned.pdf", "scanned", "./out")

# 常规 PDF：不启用 OCR，仅提取内嵌文本
ocr_config = PdfOcrConfig(do_ocr=False)
converter = DocumentToMarkdownConverter(pdf_ocr_config=ocr_config)
out_path = converter.convert("normal.pdf", "normal", "./out")

# 关闭进度条
converter = DocumentToMarkdownConverter(show_progress=False)
out_path = converter.convert("doc.pdf", "out", "./out")

# 批量转换（显示整体进度条）
paths = ["a.pdf", "b.docx", "c.pptx"]
out_paths = converter.convert_all(paths, save_dir="./out", show_progress=True)

# 内嵌图片：默认 referenced（生成 artifacts 目录并引用）；可选 embedded（Base64 内嵌，不推荐）
converter = DocumentToMarkdownConverter(image_export_mode=ImageExportMode.REFERENCED)
out_path = converter.convert("with_images.docx", "out", "./out")  # 会生成 out_artifacts/ 及 PNG
```

### 按格式的便捷函数

```python
from utils.markdown_sdk import (
    pdf_to_markdown,           # 常规 PDF，可选 use_ocr / ocr_backend
    scanned_pdf_to_markdown,   # 扫描 PDF，默认 RapidOCR，可通过 ocr_backend 切换
    docx_to_markdown,
    pptx_to_markdown,
    xlsx_to_markdown,
)

# 常规 PDF：默认不启用 OCR，仅依赖内嵌文本
pdf_to_markdown("doc.pdf", "doc", "./out")

# 常规 PDF + RapidOCR
pdf_to_markdown("scan.pdf", "scan_rapid", "./out",
                use_ocr=True, ocr_backend=OcrBackend.RAPID_OCR)

# 常规 PDF + PaddleOCR
pdf_to_markdown("scan.pdf", "scan_paddle", "./out",
                use_ocr=True, ocr_backend=OcrBackend.PADDLE_OCR)

# 扫描 PDF：默认使用 RapidOCR
scanned_pdf_to_markdown("scan.pdf", "scan_default", "./out")

# 扫描 PDF：自动选择 OCR 后端
scanned_pdf_to_markdown("scan.pdf", "scan_auto", "./out",
                        ocr_backend=OcrBackend.AUTO)

docx_to_markdown("doc.docx", "doc", "./out")
pptx_to_markdown("doc.pptx", "doc", "./out")
xlsx_to_markdown("doc.xlsx", "doc", "./out")
```

### 文档内嵌图片导出（--image-export-mode）

对应 docling CLI 的 `--image-export-mode`，控制文档内图片在 Markdown 中的处理方式：

- **`ImageExportMode.REFERENCED`**（默认）：图片导出到与 MD 同目录下的 `{输出文件名}_artifacts` 目录（PNG），MD 中以相对路径引用，如 `![Image](out_artifacts/image_000012_xxx.png)`。推荐使用。
- **`ImageExportMode.EMBEDDED`**：图片以 Base64 内嵌到 Markdown 中，不生成外部文件。不推荐，资源应与主文件分开存放。

不配置时默认为 `referenced`。

```python
from utils.markdown_sdk import DocumentToMarkdownConverter, ImageExportMode

# 默认 referenced
converter = DocumentToMarkdownConverter()
converter.convert("doc.docx", "out", "./out")  # 生成 out.md 与 out_artifacts/

# 显式指定 embedded（不推荐）
converter = DocumentToMarkdownConverter(image_export_mode=ImageExportMode.EMBEDDED)
converter.convert("doc.docx", "out", "./out")
```

### PDF OCR 配置

`PdfOcrConfig` 与 `OcrBackend` 用于控制 PDF 的 OCR 行为：

- **OcrBackend**：`AUTO`、`RAPID_OCR`、`EASY_OCR`、`TESSERACT`、`TESSERACT_CLI`、`OCR_MAC`、`PADDLE_OCR`（RapidOCR 的 paddle 后端）、`MINER_U` / `DEEPSEEK_OCR`（预留）
- **PdfOcrConfig**：`do_ocr`、`backend`、`rapid_ocr_backend`（onnxruntime / openvino / paddle / torch）、`lang`、`force_full_page_ocr`、自定义模型路径等

示例：使用 Paddle 后端（需对应环境）：

```python
from utils.markdown_sdk import DocumentToMarkdownConverter, PdfOcrConfig, OcrBackend

config = PdfOcrConfig(
    do_ocr=True,
    backend=OcrBackend.PADDLE_OCR,  # 或 RAPID_OCR + rapid_ocr_backend="paddle"
)
converter = DocumentToMarkdownConverter(pdf_ocr_config=config)
converter.convert("file.pdf", "out", "./out")
```

也可以不直接构造 `PdfOcrConfig`，而是在便捷函数中通过 `ocr_backend` 切换：

```python
from pathlib import Path
from utils.markdown_sdk import pdf_to_markdown, scanned_pdf_to_markdown, OcrBackend

pdf = Path("scan.pdf")

# 常规 PDF + RapidOCR
pdf_to_markdown(pdf, "with_rapid", "./out", use_ocr=True, ocr_backend=OcrBackend.RAPID_OCR)

# 常规 PDF + PaddleOCR
pdf_to_markdown(pdf, "with_paddle", "./out", use_ocr=True, ocr_backend=OcrBackend.PADDLE_OCR)

# 扫描 PDF + 自动选择 OCR 后端
scanned_pdf_to_markdown(pdf, "scanned_auto", "./out", ocr_backend=OcrBackend.AUTO)
```

### 综合 SDK：Docling + MinerU

本 SDK 还提供统一的 `MarkdownConverter` 抽象，可在 **Docling** 与 **MinerU** 之间切换底层引擎：

```python
from pathlib import Path
from utils.markdown_sdk import MarkdownConverter, MarkdownEngine, OcrBackend, PdfOcrConfig

pdf = Path("scan.pdf")

# 1. 使用 Docling 作为底层引擎
docling_cfg = PdfOcrConfig(do_ocr=True, backend=OcrBackend.RAPID_OCR)
docling_converter = MarkdownConverter(
    engine=MarkdownEngine.DOCLING,
    pdf_ocr_config=docling_cfg,
)
out_docling = docling_converter.convert(pdf, "docling_engine", "./out")

# 2. 使用 MinerU 作为底层引擎（需先按下方步骤安装 mineru 并准备好 VLM 模型）
mineru_converter = MarkdownConverter(engine=MarkdownEngine.MINERU)
out_mineru = mineru_converter.convert(pdf, "mineru_engine", "./out")
```

**MinerU 使用步骤：**

1. **安装 MinerU**  
   ```bash
   pip install mineru
   ```

2. **首次使用：从 ModelScope 下载 VLM 模型**  
   - 可通过 MinerU 自带的模型下载命令（如 `mineru download` 或官方文档中的下载脚本）从 [ModelScope](https://www.modelscope.cn) 拉取 VLM 模型（例如 `OpenDataLab/MinerU2.5-2509-1.2B`）。  
   - 首次运行且未配置为本地模型时，可设置环境变量 `MINERU_MODEL_SOURCE=modelscope`，MinerU 会从 ModelScope 下载到本地缓存目录（如 `C:\Users\<用户>\.cache\modelscope\hub\models\OpenDataLab\MinerU2.5-2509-1.2B`，或名称规范化后的路径）。  
   - 下载完成后，MinerU 会在用户目录下生成配置文件（如 `mineru.json`），并提示 “VLM models downloaded successfully”。

3. **已下载模型后：使用本地模型，避免再次拉取**  
   - 模型已下载到本机后，建议设置 **`MINERU_MODEL_SOURCE=local`**，后续转换将直接使用本地缓存，不再联网。  
   - 可在运行本 SDK 或 `main.py` 前设置环境变量，例如：  
     ```bash
     set MINERU_MODEL_SOURCE=local
     python main.py
     ```  
     或在代码中（在调用 MinerU 转换之前）：  
     ```python
     import os
     os.environ["MINERU_MODEL_SOURCE"] = "local"
     ```

4. **在代码中选用 MinerU 引擎**  
   - 使用 `MarkdownConverter(engine=MarkdownEngine.MINERU)` 进行转换即可（见上方代码示例）。

Docling 路线复用本项目的 `DocumentToMarkdownConverter`；MinerU 路线使用 MinerU 官方 Python 模块（VLM 分析 + 合并输出），需按上述步骤安装 mineru 并准备好 VLM 模型（首次从 ModelScope 下载，之后用 `MINERU_MODEL_SOURCE=local` 使用本地模型）。

### 示例脚本：`main.py`

项目根目录下的 `main.py` 提供与上文「各类型文件转 Markdown」对应的**可运行用例**，并支持**串行**或**并行**执行，执行日志写入 `tests/logs/{方法名}.log`。

- **方式一（串行）**：在 `if __name__ == "__main__"` 中按需取消注释要跑的用例，例如  
  `_run_one_test(scanpdf_run_markdown_converter_with_docling)`，运行后会在控制台输出并同步写入 `tests/logs/scanpdf_run_markdown_converter_with_docling.log`。
- **方式二（并行）**：取消注释 `run_all_tests_parallel()`，会使用多进程并行执行全部 `TEST_CASES` 中的用例，每个用例的 stdout 写入对应的 `tests/logs/{方法名}.log`，主进程打印每条用例的完成状态（成功返回路径或失败异常）。

运行方式：

```bash
python main.py
```

可根据需要修改各用例内部的路径（如 `tests/raw_file/xxx.pdf`）或切换为串行单用例调试。

## 许可证

MIT
