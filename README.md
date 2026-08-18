# preprocess_file

按文件特征分流的预处理流水线：识别类型 → 安全校验 → 专属解析 → 统一输出 JSON / Markdown。

## 安装

```bash
pip install -e ".[dev]"
# 扫描件 / 图片 OCR（可选）
pip install -e ".[ocr]"
```

## 用法

```python
from preprocess_file import process

doc = process("contract.pdf")
print(doc.to_markdown())
print(doc.to_dict())
```

```bash
preprocess-file invoice.xlsx --md
python -m preprocess_file scan.pdf --json --no-ocr
```

## 一期范围

- 已实现：PDF 页级分流、DOCX、PPTX、XLSX/CSV、图片、HTML、TXT/MD/JSON、EML 附件递归、ZIP/EPUB 解包
- 明确降级：`.doc/.ppt/.xls/.msg` 需先转 OOXML；音视频仅识别类型，转写留到二期
