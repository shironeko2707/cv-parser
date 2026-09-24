"""
Layout-aware text extraction from PDF and DOCX files.
Handles multi-column layouts, tables, sidebars, and structured form PDFs.
"""
import re
import pymupdf
import docx
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    page: int
    is_bold: bool = False
    font_size: float = 0.0


@dataclass
class ExtractedDocument:
    raw_text: str
    blocks: list[TextBlock]
    layout_text: str
    tables: list[list[list[str]]]
    source_path: str


# Noise patterns to strip from extracted text
NOISE_PATTERNS = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+$", re.IGNORECASE),
    re.compile(r"^Trang\s+\d+\s*/\s*\d+$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),  # "1/3"
    re.compile(r"^I accept the\b", re.IGNORECASE),
    re.compile(r"^I commit not to\b", re.IGNORECASE),
    re.compile(r"^TRUE$|^FALSE$"),
    re.compile(r"^_{4,}\s*$"),
    re.compile(r"^(Approved|Pending)\s+_{3,}", re.IGNORECASE),
]

# Form label patterns — these are field labels, not data
FORM_LABEL_PATTERNS = [
    re.compile(r"^(Từ|Tới|From|To)\s*\*\s*$", re.IGNORECASE),
    re.compile(r"\*\s*$"),  # anything ending with *
    re.compile(r"^(Name of company|Tên đơn vị công tác|Chức vụ|Position_W|Lý do thôi việc)\s*\*?\s*$", re.IGNORECASE),
    re.compile(r"^(Các thông tin bắt buộc|Required information)\s*\*?\s*$", re.IGNORECASE),
    re.compile(r"^BẠN BIẾT THÔNG TIN TUYỂN DỤNG", re.IGNORECASE),
    re.compile(r"^(DISCIPLINE|KỶ LUẬT)\s*$", re.IGNORECASE),
    re.compile(r"^(Chi tiết về|Details about)", re.IGNORECASE),
    re.compile(r"^(Giải thích cho vị trí|Explain for position)", re.IGNORECASE),
    re.compile(r"^(Approved|Pending)\s*_{2,}", re.IGNORECASE),
    re.compile(r"^(Applicant\s+)?Signature\b", re.IGNORECASE),
    re.compile(r"^Signature\s*/\s*Date", re.IGNORECASE),
    re.compile(r"^_{4,}\s*$"),
]


def is_noise(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(text):
            return True
    return False


def is_form_label(text: str) -> bool:
    text = text.strip()
    for pat in FORM_LABEL_PATTERNS:
        if pat.search(text):
            return True
    return False


def extract_pdf(filepath: str | Path) -> ExtractedDocument:
    doc = pymupdf.open(str(filepath))
    all_blocks: list[TextBlock] = []
    all_tables: list[list[list[str]]] = []

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            lines_text = []
            max_font_size = 0.0
            has_bold = False
            for line in block["lines"]:
                spans_text = []
                for span in line["spans"]:
                    spans_text.append(span["text"])
                    max_font_size = max(max_font_size, span["size"])
                    if "bold" in span["font"].lower() or span["flags"] & 2**4:
                        has_bold = True
                lines_text.append("".join(spans_text))

            text = "\n".join(lines_text).strip()
            if not text or is_noise(text):
                continue

            bbox = block["bbox"]
            all_blocks.append(TextBlock(
                x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3],
                text=text, page=page_num,
                is_bold=has_bold, font_size=max_font_size,
            ))

        try:
            tabs = page.find_tables()
            for tab in tabs:
                table_data = tab.extract()
                if table_data:
                    cleaned = []
                    for row in table_data:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        # Skip rows that are all empty or all noise
                        if any(c and not is_noise(c) and not is_form_label(c) for c in cleaned_row):
                            cleaned.append(cleaned_row)
                    if cleaned:
                        all_tables.append(cleaned)
        except Exception:
            pass

    doc.close()

    raw_text = "\n".join(b.text for b in all_blocks)
    layout_text = _reconstruct_layout(all_blocks)

    return ExtractedDocument(
        raw_text=raw_text,
        blocks=all_blocks,
        layout_text=layout_text,
        tables=all_tables,
        source_path=str(filepath),
    )


def extract_docx(filepath: str | Path) -> ExtractedDocument:
    document = docx.Document(str(filepath))
    all_blocks: list[TextBlock] = []
    all_tables: list[list[list[str]]] = []
    y_pos = 0.0

    for para in document.paragraphs:
        text = para.text.strip()
        if not text or is_noise(text):
            y_pos += 15
            continue

        is_bold = any(run.bold for run in para.runs if run.bold is not None)
        font_size = 11.0
        for run in para.runs:
            if run.font.size:
                font_size = run.font.size.pt
                break

        all_blocks.append(TextBlock(
            x0=0, y0=y_pos, x1=500, y1=y_pos + font_size + 4,
            text=text, page=0,
            is_bold=is_bold, font_size=font_size,
        ))
        y_pos += font_size + 8

    for table in document.tables:
        table_data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            if any(c and not is_noise(c) for c in row_data):
                table_data.append(row_data)
        if table_data:
            all_tables.append(table_data)

    raw_text = "\n".join(b.text for b in all_blocks)

    return ExtractedDocument(
        raw_text=raw_text,
        blocks=all_blocks,
        layout_text=raw_text,
        tables=all_tables,
        source_path=str(filepath),
    )


def extract(filepath: str | Path) -> ExtractedDocument:
    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return extract_docx(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _reconstruct_layout(blocks: list[TextBlock]) -> str:
    if not blocks:
        return ""

    pages: dict[int, list[TextBlock]] = {}
    for b in blocks:
        pages.setdefault(b.page, []).append(b)

    full_text_parts = []

    for page_num in sorted(pages.keys()):
        page_blocks = pages[page_num]
        if not page_blocks:
            continue

        page_width = max(b.x1 for b in page_blocks)
        columns = _detect_columns(page_blocks, page_width)

        for col_blocks in columns:
            col_blocks.sort(key=lambda b: b.y0)
            for b in col_blocks:
                if b.is_bold or b.font_size > 12:
                    full_text_parts.append(f"\n[SECTION] {b.text}")
                else:
                    full_text_parts.append(b.text)

    return "\n".join(full_text_parts)


def _detect_columns(blocks: list[TextBlock], page_width: float) -> list[list[TextBlock]]:
    if not blocks or page_width <= 0:
        return [blocks]

    x_centers = [((b.x0 + b.x1) / 2) for b in blocks]
    midpoint = page_width / 2

    left = [b for b, xc in zip(blocks, x_centers) if xc < midpoint * 0.85]
    right = [b for b, xc in zip(blocks, x_centers) if xc >= midpoint * 0.85]

    if len(left) >= 3 and len(right) >= 3:
        left_max_x = max(b.x1 for b in left) if left else 0
        right_min_x = min(b.x0 for b in right) if right else page_width
        gap = right_min_x - left_max_x

        if gap > 20:
            return [left, right]

    blocks_sorted = sorted(blocks, key=lambda b: (b.y0, b.x0))
    return [blocks_sorted]


def extract_key_value_pairs(doc: ExtractedDocument) -> dict[str, str]:
    """
    Extract key:value pairs from the document.
    Filters out form labels and noise.
    """
    pairs: dict[str, str] = {}

    for block in doc.blocks:
        lines = [l.strip() for l in block.text.split("\n") if l.strip()]

        # Multi-line blocks without colons: "label\nvalue" pattern (structured forms)
        if len(lines) >= 2 and not any(":" in l for l in lines):
            for j in range(0, len(lines) - 1, 2):
                label = lines[j]
                val = lines[j + 1]
                if (len(label) < 40 and len(label.split()) <= 5
                        and not is_form_label(label) and not is_noise(label)
                        and not is_form_label(val) and not is_noise(val)):
                    pairs[label] = val

        for idx, line in enumerate(lines):
            if is_form_label(line) or is_noise(line):
                continue
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if is_form_label(key) or is_noise(key):
                    continue
                if key and val and len(key) < 60:
                    # Append continuation lines (value ends with comma)
                    full_val = val
                    j = idx + 1
                    while j < len(lines) and full_val.rstrip().endswith(","):
                        nxt = lines[j].strip()
                        if not nxt or is_form_label(nxt) or is_noise(nxt) or ":" in nxt:
                            break
                        full_val = full_val.rstrip() + " " + nxt
                        j += 1
                    pairs[key] = full_val
                elif key and not val and idx + 1 < len(lines):
                    next_line = lines[idx + 1]
                    if not is_form_label(next_line) and not is_noise(next_line):
                        pairs[key] = next_line

    for table in doc.tables:
        for row in table:
            cleaned = [c for c in row if c and not is_noise(c) and not is_form_label(c)]
            if len(cleaned) == 2 and len(cleaned[0]) < 60:
                pairs[cleaned[0]] = cleaned[1]
            elif len(cleaned) == 4:
                if len(cleaned[0]) < 60:
                    pairs[cleaned[0]] = cleaned[1]
                if len(cleaned[2]) < 60:
                    pairs[cleaned[2]] = cleaned[3]

    sorted_blocks = sorted(doc.blocks, key=lambda b: (b.page, b.y0, b.x0))
    for i in range(len(sorted_blocks) - 1):
        curr = sorted_blocks[i]
        nxt = sorted_blocks[i + 1]
        if abs(curr.y0 - nxt.y0) < 5 and curr.x1 < nxt.x0:
            label = curr.text.rstrip(":").strip()
            if label and len(label) < 60 and not is_form_label(label):
                val = nxt.text.strip()
                if not is_noise(val) and not is_form_label(val):
                    pairs[label] = val

    return pairs


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        doc = extract(sys.argv[1])
        print(f"=== Source: {doc.source_path} ===")
        print(f"Blocks: {len(doc.blocks)}")
        print(f"Tables: {len(doc.tables)}")
        print(f"\n=== Layout Text ===")
        print(doc.layout_text[:2000])
        print(f"\n=== Key-Value Pairs ===")
        kv = extract_key_value_pairs(doc)
        for k, v in kv.items():
            print(f"  {k}: {v}")
    else:
        print("Usage: python text_extractor.py <file.pdf|file.docx>")
