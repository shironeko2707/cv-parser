"""
Layout-aware text extraction for CVs in any common document format.

Supported inputs
    PDF (digital)          PyMuPDF line/span geometry
    PDF (scanned) / images OCR through PyMuPDF + Tesseract (if installed)
    DOCX                   body order incl. tables, text boxes, headers/footers
    DOC / RTF / ODT        converted to DOCX with LibreOffice (if installed)
    TXT / MD / HTML        plain parsing

Output: an ExtractedDocument whose `layout_text` is the reading-order text the
LLM sees. It uses a small, stable markup that the fine-tuned SLM is trained on:

    ## EDUCATION                      <- detected section heading
    Senior Engineer | Jan 2020 - Now  <- same-baseline fragments joined by " | "
    • Built ...                       <- normalized bullets
    Company | Title | From | To       <- table rows, cells joined by " | "

What it handles that naive extraction gets wrong:
    - multi-column / sidebar layouts (whitespace-gutter detection, any width)
    - right-aligned dates / labels kept on the same row as their text
    - wrapped lines re-joined (incl. de-hyphenation)
    - tables emitted once, as rows (not duplicated as loose text)
    - repeated page headers/footers and page numbers removed
    - Vietnamese text NFC-normalized, icon-font glyphs and ligatures cleaned
    - hyperlinks collected (LinkedIn/GitHub icons often only exist as links)
"""
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import docx
import pymupdf

from sections import is_document_title, match_section
from text_utils import clean_line, is_bullet, join_wrapped, normalize_label

OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "vie+eng")
OCR_DPI = int(os.environ.get("OCR_DPI", "300"))

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".rtf", ".odt", ".txt", ".md", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


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
    is_heading: bool = False
    section: str | None = None


@dataclass
class ExtractedDocument:
    raw_text: str
    blocks: list[TextBlock]
    layout_text: str
    tables: list[list[list[str]]]
    source_path: str
    links: list[str] = field(default_factory=list)
    page_count: int = 1
    ocr_used: bool = False
    file_type: str = ""
    warnings: list[str] = field(default_factory=list)


# Noise patterns to strip from extracted text
NOISE_PATTERNS = [
    re.compile(r"^(Page|Trang|Seite|Página)\s*\d+(\s*(of|/|trên|von|de)\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^-?\s*\d{1,2}\s*-?$"),  # bare page number "3" / "- 3 -"
    re.compile(r"^\d{1,3}\s*/\s*\d{1,3}$"),  # "1/3" (not dates like 09/2012)
    re.compile(r"^I accept the\b", re.IGNORECASE),
    re.compile(r"^I commit not to\b", re.IGNORECASE),
    re.compile(r"^TRUE$|^FALSE$"),
    re.compile(r"^_{4,}\s*$"),
    re.compile(r"^[.\-_=~*•]{3,}$"),
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


# ===========================================================================
# Format-independent row model + renderer
# ===========================================================================

@dataclass
class _Row:
    """One visual line of text (or one table row) in reading order."""
    text: str
    size: float = 11.0
    bold: bool = False
    page: int = 0
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    is_table: bool = False
    style_heading: bool = False  # DOCX "Heading n"/"Title" style, HTML <h1-6>
    para_break: bool = False     # blank line before this row
    cells: list | None = None    # PDF: same-baseline segment texts


def _body_font_size(rows: list[_Row]) -> float:
    """Font size carrying most of the characters (the body text size)."""
    weights: Counter = Counter()
    for r in rows:
        if not r.is_table and r.size > 0:
            weights[round(r.size * 2) / 2] += len(r.text)
    if not weights:
        return 11.0
    return weights.most_common(1)[0][0]


_HAS_DIGIT_HEAVY_RE = re.compile(r"\d.*\d.*\d")


def _heading_section(row: _Row, body_size: float, name_row: _Row | None) -> tuple[bool, str | None]:
    """Decide whether a row is a section heading. Returns (is_heading, section_key)."""
    if row.is_table or row is name_row:
        return False, None
    text = row.text.strip()
    if is_bullet(text) or len(text) > 70 or len(text.split()) > 9 or "@" in text:
        return False, None
    section = match_section(text)
    if section:
        return True, section
    if is_document_title(text):
        return False, None
    letters = [c for c in text if c.isalpha()]
    is_upper = bool(letters) and all(not c.islower() for c in letters)
    bigger = row.size >= body_size * 1.2
    styled = row.bold or is_upper or bigger or row.style_heading
    if styled and not text.endswith((".", ",", ";")) and "|" not in text:
        section = match_section(text, loose=True)
        if section:
            return True, section
    if text.endswith((".", ",", ";")) or _HAS_DIGIT_HEAVY_RE.search(text) or "|" in text:
        return False, None
    if len(letters) < 3:
        return False, None
    if row.style_heading and (bigger or row.bold or is_upper):
        return True, None
    if bigger and (row.bold or is_upper) and len(text.split()) <= 5:
        return True, None
    return False, None


def _render(rows: list[_Row]) -> tuple[str, str, list[TextBlock]]:
    """Render ordered rows into (layout_text, raw_text, blocks)."""
    body_size = _body_font_size(rows)
    # The candidate's name is normally the largest text near the top of page 1:
    # never tag it as a section heading.
    name_row = None
    first_rows = [r for r in rows[:12] if not r.is_table and r.page == 0]
    if first_rows:
        top = max(first_rows, key=lambda r: r.size)
        if top.size >= body_size * 1.2 and not match_section(top.text):
            name_row = top

    layout: list[str] = []
    raw: list[str] = []
    blocks: list[TextBlock] = []
    for r in rows:
        is_heading, section = _heading_section(r, body_size, name_row)
        if is_heading:
            if layout and layout[-1] != "":
                layout.append("")
            layout.append(f"## {r.text}")
        else:
            if r.para_break and layout and layout[-1] != "":
                layout.append("")
            layout.append(r.text)
        raw.append(r.text)
        blocks.append(TextBlock(
            x0=r.x0, y0=r.y0, x1=r.x1, y1=r.y1, text=r.text, page=r.page,
            is_bold=r.bold, font_size=r.size, is_heading=is_heading, section=section,
        ))
    layout_text = "\n".join(layout).strip()
    layout_text = re.sub(r"\n{3,}", "\n\n", layout_text)
    return layout_text, "\n".join(raw), blocks


def _dedupe_links(links: list[str]) -> list[str]:
    seen, out = set(), []
    for link in links:
        link = link.strip()
        if link.lower().startswith("mailto:"):
            link = link[7:].split("?")[0]
        elif link.lower().startswith("tel:"):
            link = link[4:]
        key = link.lower().rstrip("/")
        if link and key not in seen and not key.startswith(("#", "file:", "javascript:")):
            seen.add(key)
            out.append(link)
    return out


# ===========================================================================
# PDF
# ===========================================================================

@dataclass
class _Line:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    size: float
    bold: bool
    page: int
    is_table: bool = False
    col_x0: float = 0.0  # bounds of the leaf column this line was assigned to
    col_x1: float = 0.0

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return max(self.y1 - self.y0, 1.0)


_BOLD_FONT_RE = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)


def _span_is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or bool(_BOLD_FONT_RE.search(span.get("font", "")))


def _page_lines(page, page_num: int, textpage=None) -> list[_Line]:
    """Split the page into visual line segments. A big horizontal gap inside a
    PyMuPDF line starts a new segment, so columns/right-aligned dates stay
    separate items for the layout analysis."""
    d = page.get_text("dict", textpage=textpage) if textpage else page.get_text("dict")
    out: list[_Line] = []
    for block in d["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            dx, dy = line.get("dir", (1, 0))
            if abs(dx) < 0.95:  # rotated/vertical decoration text
                continue
            segs: list[list[dict]] = []
            last_x1 = None
            for span in line["spans"]:
                if not span["text"].strip():
                    continue
                gap_limit = max(span["size"] * 2.0, 12)
                if last_x1 is None or span["bbox"][0] - last_x1 > gap_limit:
                    segs.append([span])
                else:
                    segs[-1].append(span)
                last_x1 = span["bbox"][2]
            for seg in segs:
                parts = []
                prev = None
                for sp in seg:
                    if prev is not None:
                        gap = sp["bbox"][0] - prev["bbox"][2]
                        if gap > sp["size"] * 0.15 and not parts[-1].endswith(" ") \
                                and not sp["text"].startswith(" "):
                            parts.append(" ")
                    parts.append(sp["text"])
                    prev = sp
                text = clean_line("".join(parts))
                if not text:
                    continue
                chars = sum(len(sp["text"].strip()) for sp in seg) or 1
                bold_chars = sum(len(sp["text"].strip()) for sp in seg if _span_is_bold(sp))
                size = max(sp["size"] for sp in seg)
                out.append(_Line(
                    x0=seg[0]["bbox"][0], y0=min(sp["bbox"][1] for sp in seg),
                    x1=seg[-1]["bbox"][2], y1=max(sp["bbox"][3] for sp in seg),
                    text=text, size=round(size, 1), bold=bold_chars / chars >= 0.6,
                    page=page_num,
                ))
    return out


def _page_tables(page, page_num: int) -> list[tuple[pymupdf.Rect, list[list[str]]]]:
    """Real data tables (ruled). Whole-page layout grids are ignored so the
    column logic can read them as columns instead."""
    try:
        if len(page.get_drawings()) < 4:
            return []
        found = page.find_tables()
    except Exception:
        return []
    page_area = page.rect.width * page.rect.height
    out = []
    for tab in found.tables:
        try:
            data = tab.extract()
        except Exception:
            continue
        rows = []
        for row in data:
            cells = [clean_line((c or "").replace("\n", " ")) for c in row]
            if any(c and not is_noise(c) for c in cells):
                rows.append(cells)
        if len(rows) < 2 or max(len(r) for r in rows) < 2:
            continue
        rect = pymupdf.Rect(tab.bbox)
        max_cell_lines = max(((c or "").count("\n") + 1 for row in data for c in row), default=1)
        is_layout = (rect.width * rect.height > 0.5 * page_area and len(rows) <= 4) or \
                    (max(len(r) for r in rows) <= 3 and max_cell_lines > 8)
        if not is_layout:
            out.append((rect, rows))
    return out


def _table_row_text(cells: list[str]) -> str:
    """Join cells with " | ", keeping empty interior cells so columns stay aligned."""
    cells = list(cells)
    while cells and not cells[-1]:
        cells.pop()
    while cells and not cells[0]:
        cells.pop(0)
    return " | ".join(cells)


def _merge_rows(lines: list[_Line]) -> list[list[_Line]]:
    """Group line segments sharing a baseline into visual rows, top to bottom."""
    rows: list[list[_Line]] = []
    for ln in sorted(lines, key=lambda l: (l.yc, l.x0)):
        if rows and not ln.is_table and not rows[-1][0].is_table:
            ref = rows[-1]
            ry0 = min(l.y0 for l in ref)
            ry1 = max(l.y1 for l in ref)
            overlap = min(ry1, ln.y1) - max(ry0, ln.y0)
            if overlap > 0.5 * min(ln.h, ry1 - ry0):
                ref.append(ln)
                continue
        rows.append([ln])
    for i, r in enumerate(rows):
        r.sort(key=lambda l: l.x0)
        deduped = [r[0]]
        for l in r[1:]:  # text drawn twice (fake bold / shadow effects)
            if l.text != deduped[-1].text:
                deduped.append(l)
        rows[i] = deduped
    return rows


def _find_gutter(lines: list[_Line], x_min: float, x_max: float) -> tuple[float, float] | None:
    """Find a vertical whitespace gutter separating two text columns."""
    width = x_max - x_min
    if width < 150 or len(lines) < 6:
        return None
    narrow = [l for l in lines if (l.x1 - l.x0) < 0.62 * width]
    if len(narrow) < 6:
        return None
    lo, hi = int(x_min + 0.12 * width), int(x_max - 0.12 * width)
    if hi <= lo:
        return None
    cover = [0] * (hi - lo + 1)
    for l in narrow:
        a, b = max(int(l.x0), lo), min(int(l.x1), hi)
        for x in range(a, b + 1):
            cover[x - lo] += 1
    best, run_start = None, None
    for i, c in enumerate(cover + [1]):
        if c == 0 and run_start is None:
            run_start = i
        elif c != 0 and run_start is not None:
            g0, g1 = lo + run_start, lo + i - 1
            if g1 - g0 >= 4:
                left = sum(1 for l in narrow if l.x1 <= g0 + 1)
                right = sum(1 for l in narrow if l.x0 >= g1 - 1)
                if left >= 4 and right >= 4:
                    score = (g1 - g0) - 0.1 * abs((g0 + g1) / 2 - (x_min + x_max) / 2)
                    if best is None or score > best[0]:
                        best = (score, g0, g1)
            run_start = None
    if not best:
        return None
    return float(best[1]), float(best[2])


_DATEISH_RE = re.compile(
    r"(19|20)\d{2}|\b\d{1,2}[/.-]\d{2,4}\b|present|current|now|nay|hiện tại|"
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|:$",
    re.IGNORECASE,
)


def _aligned_fraction(a: list[_Line], b: list[_Line]) -> float:
    """Share of lines in `a` that sit on the same baseline as some line in `b`."""
    if not a:
        return 0.0
    hits = sum(1 for x in a if any(abs(x.yc - y.yc) < 0.5 * min(x.h, y.h) for y in b))
    return hits / len(a)


def _texty(lines: list[_Line]) -> float:
    """Share of lines that are running text (long or bullet) rather than short fields."""
    if not lines:
        return 0.0
    return sum(1 for l in lines if len(l.text) > 32 or is_bullet(l.text)) / len(lines)


def _is_row_layout(left: list[_Line], right: list[_Line]) -> bool:
    """True when the two "columns" are really one column of rows: right-aligned
    dates/locations, a date column in front of entries, or label/value forms.
    Real columns (sidebar + main) both carry running text, and baselines only
    line up by coincidence."""
    if not left or not right:
        return True
    align = max(_aligned_fraction(right, left), _aligned_fraction(left, right))
    if align < 0.6:
        return False
    short_side = left if _texty(left) <= _texty(right) else right
    dateish = sum(1 for l in short_side if _DATEISH_RE.search(l.text)) / len(short_side)
    if dateish >= 0.5:
        return True  # date column / right-aligned dates
    if any(match_section(l.text) for l in left) and any(match_section(l.text) for l in right):
        return False  # section headings on both sides: two real columns of short items
    return _texty(left) < 0.25 and _texty(right) < 0.25  # label/value form


def _order_region(lines: list[_Line], x_min: float, x_max: float, depth: int = 0) -> list[list[_Line]]:
    """Recursive column-aware ordering. Returns rows in reading order."""
    if depth < 2:
        gutter = _find_gutter([l for l in lines if not l.is_table], x_min, x_max)
        if gutter:
            g0, g1 = gutter
            spanning = [l for l in lines if l.x0 < g0 - 1 and l.x1 > g1 + 1]
            left_all = [l for l in lines if l not in spanning and l.x1 <= g0 + 1]
            right_all = [l for l in lines if l not in spanning and l.x0 >= g1 - 1]
            if len(spanning) <= 0.3 * len(lines) and not _is_row_layout(left_all, right_all):
                # bands separated by full-width items (header, section rules)
                out: list[list[_Line]] = []
                cuts = sorted(spanning, key=lambda l: l.y0)
                prev_y = float("-inf")
                for cut in cuts + [None]:
                    band_end = cut.y0 if cut else float("inf")
                    band = [l for l in lines if l not in spanning and prev_y <= l.yc < band_end]
                    left = [l for l in band if l.x1 <= g0 + 1]
                    right = [l for l in band if l not in left]
                    if left:
                        out.extend(_order_region(left, x_min, g0, depth + 1))
                    if right:
                        out.extend(_order_region(right, g1, x_max, depth + 1))
                    if cut:
                        out.extend(_merge_rows([cut]))
                        prev_y = cut.yc
                return out
    cx0 = min(l.x0 for l in lines)
    cx1 = max(l.x1 for l in lines)
    for l in lines:
        l.col_x0, l.col_x1 = cx0, cx1
    return _merge_rows(lines)


# "Phone: ...", "Ngày sinh: ..." -- a new labelled line, never a wrapped continuation
_LABEL_START_RE = re.compile(r"^[^\W\d][\w .'/&-]{0,25}:\s")


def _rows_from_pdf_rows(line_rows: list[list[_Line]], tables: dict[int, list[list[str]]]) -> list[_Row]:
    """Convert geometric rows into _Rows, re-joining wrapped lines."""
    out: list[_Row] = []
    prev_geo: list[_Line] | None = None
    for geo in line_rows:
        first = geo[0]
        if first.is_table:
            for i, cells in enumerate(tables[id(first)]):
                out.append(_Row(
                    text=_table_row_text(cells), page=first.page, is_table=True,
                    x0=first.x0, y0=first.y0, x1=first.x1, y1=first.y1, para_break=(i == 0),
                ))
            prev_geo = None
            continue
        text = " | ".join(l.text for l in geo)
        if prev_geo is not None and out and _merge_wrapped_cells(out[-1], prev_geo, geo):
            prev_geo = geo
            continue
        size = max(l.size for l in geo)
        bold = all(l.bold for l in geo)
        x0, x1 = geo[0].x0, geo[-1].x1
        y0, y1 = min(l.y0 for l in geo), max(l.y1 for l in geo)
        para_break = False
        if prev_geo is not None and out:
            prev = out[-1]
            gap = y0 - prev.y1
            if prev.page != first.page:
                para_break = True
            elif gap < -2 or abs(x0 - prev.x0) > 30:
                para_break = gap > size * 0.9
            else:
                p = prev_geo[-1]
                col_w = max(p.col_x1 - p.col_x0, 1.0)
                continuation = (
                    text[:1].islower() or text[:1].isdigit()
                    or prev.text.endswith((",", "-", "–", "&", "/", "(", "và", "and"))
                    or len(prev.text) >= 55
                ) and not _LABEL_START_RE.match(text)
                wraps = (
                    continuation
                    and len(geo) == 1 and len(prev_geo) == 1
                    and p.col_x0 == first.col_x0  # same leaf column
                    and gap < size * 0.6
                    and abs(size - prev.size) < 0.6 and bold == prev.bold
                    and not is_bullet(text) and not prev.text.endswith(":")
                    and prev.x1 >= p.col_x1 - 0.15 * col_w  # previous line ran to the edge
                    and x0 >= prev.x0 - 3
                    and match_section(text) is None and match_section(prev.text) is None
                )
                if wraps:
                    prev.text = join_wrapped(prev.text, text)
                    prev.x1 = max(prev.x1, x1)
                    prev.y1 = y1
                    prev_geo = geo
                    continue
                para_break = gap > size * 0.9
        out.append(_Row(text=text, size=size, bold=bold, page=first.page,
                        x0=x0, y0=y0, x1=x1, y1=y1, para_break=para_break,
                        cells=[l.text for l in geo]))
        prev_geo = geo
    return out


_LINKISH_RE = re.compile(r"@|www\.|https?://|\.(com|vn|net|org|io)\b", re.IGNORECASE)
_DANGLING_RE = re.compile(r"(?:[,&/(–-]|\b(?:to|and|of|at|đến|và|tại|tháng|thang))\s*$", re.IGNORECASE)


def _merge_wrapped_cells(prev: _Row, prev_geo: list[_Line], geo: list[_Line]) -> bool:
    """Side-by-side cells that wrap ("Company, Thừa | Tháng 5/2021 đến Tháng"
    over "Thiên Huế | 7/2023", or just "7/2023") are merged cell by cell."""
    if prev.cells is None or len(prev_geo) < 2 or len(prev.cells) != len(prev_geo) or len(geo) > len(prev_geo):
        return False
    size = max(l.size for l in geo)
    if min(l.y0 for l in geo) - prev.y1 > size * 0.6 or geo[0].page != prev.page:
        return False
    targets = []
    for l in geo:  # each piece must keep a cell's left edge (or right edge if right-aligned)
        match = [i for i, a in enumerate(prev_geo) if abs(a.x0 - l.x0) <= 4 or abs(a.x1 - l.x1) <= 4]
        if len(match) != 1 or match[0] in targets:
            return False
        targets.append(match[0])
    if any(match_section(c) for c in prev.cells):
        return False
    if not any(_DANGLING_RE.search(prev.cells[i]) or (l.text[:1].islower() and not _LINKISH_RE.search(l.text))
               for i, l in zip(targets, geo)):
        return False
    for i, l in zip(targets, geo):
        prev.cells[i] = join_wrapped(prev.cells[i], l.text)
    prev.text = " | ".join(prev.cells)
    prev.y1 = max(l.y1 for l in geo)
    return True


def _header_footer_keys(pages_lines: list[list[_Line]], heights: list[float]) -> set[str]:
    """Lines repeated in the top/bottom margin of several pages."""
    if len(pages_lines) < 2:
        return set()
    counts: Counter = Counter()
    for lines, h in zip(pages_lines, heights):
        keys = set()
        for l in lines:
            if l.y1 < 0.08 * h or l.y0 > 0.92 * h:
                keys.add(re.sub(r"\d+", "#", normalize_label(l.text)))
        counts.update(keys)
    return {k for k, c in counts.items() if c >= 2 and k}


def _ocr_textpage(page):
    return page.get_textpage_ocr(language=OCR_LANGUAGES, dpi=OCR_DPI, full=True)


def extract_pdf(filepath: str | Path, file_type: str = "pdf") -> ExtractedDocument:
    doc = pymupdf.open(str(filepath))
    return _extract_pymupdf(doc, str(filepath), file_type)


def _extract_pymupdf(doc, source: str, file_type: str) -> ExtractedDocument:
    warnings: list[str] = []
    links: list[str] = []
    ocr_used = False
    pages_lines: list[list[_Line]] = []
    pages_tables: list[list[tuple]] = []
    heights: list[float] = []
    widths: list[float] = []
    all_tables: list[list[list[str]]] = []

    for page_num, page in enumerate(doc):
        lines = _page_lines(page, page_num)
        if sum(len(l.text) for l in lines) < 30 and (page.get_images() or file_type == "image"):
            try:
                lines = _page_lines(page, page_num, textpage=_ocr_textpage(page))
                ocr_used = True
            except Exception as e:  # Tesseract missing / language data missing
                warnings.append(
                    f"Page {page_num + 1} looks scanned but OCR failed ({type(e).__name__}). "
                    f"Install Tesseract with '{OCR_LANGUAGES}' language data (TESSDATA_PREFIX)."
                )
        tables = _page_tables(page, page_num) if not ocr_used else []
        for link in page.get_links():
            if link.get("uri"):
                links.append(link["uri"])
        pages_lines.append(lines)
        pages_tables.append(tables)
        heights.append(page.rect.height)
        widths.append(page.rect.width)
    page_count = len(doc)
    doc.close()

    hf_keys = _header_footer_keys(pages_lines, heights)
    seen_hf: set[str] = set()
    rows: list[_Row] = []
    for page_num, (lines, tables) in enumerate(zip(pages_lines, pages_tables)):
        h = heights[page_num]
        kept: list[_Line] = []
        for l in lines:
            if is_noise(l.text):
                continue
            if l.y1 < 0.08 * h or l.y0 > 0.92 * h:
                key = re.sub(r"\d+", "#", normalize_label(l.text))
                if key in hf_keys:
                    if key in seen_hf:
                        continue
                    seen_hf.add(key)
            kept.append(l)

        table_map: dict[int, list[list[str]]] = {}
        for rect, trows in tables:
            kept = [l for l in kept if not rect.contains(pymupdf.Point((l.x0 + l.x1) / 2, l.yc))]
            marker = _Line(rect.x0, rect.y0, rect.x1, rect.y1, "", 0, False, page_num, is_table=True)
            table_map[id(marker)] = trows
            kept.append(marker)
            all_tables.append(trows)
        if not kept:
            continue
        x_min = min(l.x0 for l in kept)
        x_max = max(l.x1 for l in kept)
        ordered = _order_region(kept, x_min, x_max)
        page_rows = _rows_from_pdf_rows(ordered, table_map)
        if rows and page_rows:
            page_rows[0].para_break = True
        rows.extend(page_rows)

    layout_text, raw_text, blocks = _render(rows)
    if not raw_text.strip() and not warnings:
        warnings.append("No text could be extracted from the document.")
    return ExtractedDocument(
        raw_text=raw_text, blocks=blocks, layout_text=layout_text, tables=all_tables,
        source_path=source, links=_dedupe_links(links), page_count=page_count,
        ocr_used=ocr_used, file_type=file_type, warnings=warnings,
    )


def extract_image(filepath: str | Path) -> ExtractedDocument:
    img = pymupdf.open(str(filepath))
    pdf_bytes = img.convert_to_pdf()
    img.close()
    return _extract_pymupdf(pymupdf.open("pdf", pdf_bytes), str(filepath), "image")


# ===========================================================================
# DOCX
# ===========================================================================

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_TAG_P, _TAG_TBL, _TAG_TR, _TAG_TC, _TAG_SDT = (f"{_W}p", f"{_W}tbl", f"{_W}tr", f"{_W}tc", f"{_W}sdt")
_TAG_TXBX = f"{_W}txbxContent"
_SKIP_TAGS = {f"{_W}instrText", f"{_W}delText", f"{_W}fldChar", f"{_MC}Fallback", f"{_W}rPr", f"{_W}pPr"}


@dataclass
class _DocxItem:
    text: str
    size: float
    bold: bool
    heading_style: bool
    is_table_row: bool = False
    para_break: bool = False


class _DocxWalker:
    def __init__(self, document):
        self.document = document
        self.style_names: dict[str, str] = {}
        self.style_sizes: dict[str, float] = {}
        self.style_bold: dict[str, bool] = {}
        for st in document.styles:
            try:
                self.style_names[st.style_id] = (st.name or "").lower()
                font = getattr(st, "font", None)
                if font is not None:
                    if font.size:
                        self.style_sizes[st.style_id] = font.size.pt
                    if font.bold:
                        self.style_bold[st.style_id] = True
            except Exception:
                continue
        self.default_size = 11.0
        self.tables: list[list[list[str]]] = []
        self.table_depth = 0

    # -- paragraph ---------------------------------------------------------
    def _para_text(self, p, textboxes: list) -> str:
        parts: list[str] = []

        def visit(el):
            for child in el:
                tag = child.tag
                if tag in _SKIP_TAGS:
                    continue
                if tag == _TAG_TXBX:
                    textboxes.append(child)
                    continue
                if tag == f"{_W}t":
                    parts.append(child.text or "")
                elif tag == f"{_W}tab":
                    parts.append("\t")
                elif tag in (f"{_W}br", f"{_W}cr"):
                    parts.append("\n")
                else:
                    visit(child)

        visit(p)
        return "".join(parts)

    def _para_style(self, p) -> tuple[str, float, bool, bool]:
        style_id = ""
        ppr = p.find(f"{_W}pPr")
        numbered = False
        if ppr is not None:
            ps = ppr.find(f"{_W}pStyle")
            if ps is not None:
                style_id = ps.get(f"{_W}val", "")
            numbered = ppr.find(f"{_W}numPr") is not None
        size = self.style_sizes.get(style_id, 0.0)
        runs = [r for r in p.iter(f"{_W}r") if (r.findtext(f"{_W}t") or "").strip()]
        bold_runs = 0
        for r in runs:
            rpr = r.find(f"{_W}rPr")
            if rpr is None:
                continue
            sz = rpr.find(f"{_W}sz")
            if sz is not None and not size:
                try:
                    size = int(sz.get(f"{_W}val")) / 2
                except (TypeError, ValueError):
                    pass
            b = rpr.find(f"{_W}b")
            if b is not None and b.get(f"{_W}val", "true") not in ("0", "false"):
                bold_runs += 1
        bold = bool(runs) and (bold_runs == len(runs) or (self.style_bold.get(style_id, False) and bold_runs == 0))
        return self.style_names.get(style_id, ""), size or self.default_size, bold, numbered

    def paragraph(self, p) -> list[_DocxItem]:
        textboxes: list = []
        text = self._para_text(p, textboxes)
        items: list[_DocxItem] = []
        style_name, size, bold, numbered = self._para_style(p)
        heading_style = style_name.startswith(("heading", "title")) or style_name in ("subtitle",)
        numbered = numbered or style_name.startswith(("list bullet", "list number", "list paragraph"))
        for i, piece in enumerate(text.split("\n")):
            piece = re.sub(r"\t+", " | ", piece.strip("\t "))
            line = clean_line(piece)
            if not line or (is_noise(line) and not self.table_depth):
                continue
            if numbered and i == 0 and not is_bullet(line):
                line = "• " + line
            items.append(_DocxItem(line, size, bold, heading_style))
        seen = set()
        for tb in textboxes:
            for item in self.container(tb):
                if item.text not in seen:
                    seen.add(item.text)
                    items.append(item)
        return items

    # -- table -------------------------------------------------------------
    def table(self, tbl) -> list[_DocxItem]:
        grid: list[list[list[_DocxItem]]] = []
        for tr in tbl.iter(_TAG_TR):
            if tr.getparent() is not tbl and tr.getparent().getparent() is not tbl:
                continue  # nested table row: handled inside its cell
            self.table_depth += 1
            try:
                grid.append([self.container(tc) for tc in tr if tc.tag == _TAG_TC])
            finally:
                self.table_depth -= 1
        if not grid:
            return []
        rich = any(
            len(cell) >= 4 or any(match_section(it.text) or it.heading_style for it in cell)
            for row in grid for cell in row
        )
        items: list[_DocxItem] = []
        if rich:  # layout table (template grid): read cell by cell
            for row in grid:
                for cell in row:
                    if cell:
                        cell[0].para_break = True
                    items.extend(cell)
            return items
        data_rows = []
        for row in grid:
            # several paragraphs in one cell are usually list items
            cells = [" • ".join(it.text.removeprefix("• ") for it in cell) for cell in row]
            deduped = []
            for c in cells:  # horizontally merged cells repeat their text
                if not deduped or c != deduped[-1]:
                    deduped.append(c)
            if any(deduped):
                data_rows.append(deduped)
                items.append(_DocxItem(_table_row_text(deduped), self.default_size,
                                       False, False, is_table_row=True))
        if data_rows:
            self.tables.append(data_rows)
        return items

    def container(self, el) -> list[_DocxItem]:
        items: list[_DocxItem] = []
        for child in el:
            if child.tag == _TAG_P:
                items.extend(self.paragraph(child))
            elif child.tag == _TAG_TBL:
                items.extend(self.table(child))
            elif child.tag == _TAG_SDT:
                content = child.find(f"{_W}sdtContent")
                if content is not None:
                    items.extend(self.container(content))
        return items


def _docx_links(document) -> list[str]:
    links = []
    parts = [document.part]
    for section in document.sections:
        for hf in (section.header, section.footer):
            try:
                parts.append(hf.part)
            except Exception:
                pass
    for part in parts:
        for rel in part.rels.values():
            if rel.reltype.endswith("/hyperlink") and rel.is_external:
                links.append(rel.target_ref)
    return links


def extract_docx(filepath: str | Path, file_type: str = "docx") -> ExtractedDocument:
    document = docx.Document(str(filepath))
    walker = _DocxWalker(document)

    header_items: list[_DocxItem] = []
    footer_items: list[_DocxItem] = []
    seen_hf: set[str] = set()
    for section in document.sections:
        for hf, bucket in ((section.header, header_items), (section.footer, footer_items)):
            try:
                if hf.is_linked_to_previous and bucket:
                    continue
                for item in walker.container(hf._element):
                    if item.text not in seen_hf:
                        seen_hf.add(item.text)
                        bucket.append(item)
            except Exception:
                continue

    body_items = walker.container(document.element.body)
    items = header_items + body_items + footer_items

    rows: list[_Row] = []
    prev_table = False
    for i, it in enumerate(items):
        rows.append(_Row(
            text=it.text, size=it.size, bold=it.bold, is_table=it.is_table_row,
            style_heading=it.heading_style, y0=float(i), y1=float(i) + 1,
            para_break=it.para_break or (it.is_table_row != prev_table),
        ))
        prev_table = it.is_table_row
    layout_text, raw_text, blocks = _render(rows)
    return ExtractedDocument(
        raw_text=raw_text, blocks=blocks, layout_text=layout_text, tables=walker.tables,
        source_path=str(filepath), links=_dedupe_links(_docx_links(document)),
        page_count=1, file_type=file_type,
    )


# ===========================================================================
# Legacy/other formats
# ===========================================================================

def _convert_with_libreoffice(filepath: Path, target: str = "docx") -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError(
            f"Cannot read {filepath.suffix} files: LibreOffice is not installed "
            f"(apt install libreoffice-writer), or save the file as .docx/.pdf."
        )
    outdir = Path(tempfile.mkdtemp(prefix="cvconv_"))
    profile = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    try:
        subprocess.run(
            [soffice, f"-env:UserInstallation=file://{profile}", "--headless",
             "--convert-to", target, "--outdir", str(outdir), str(filepath.resolve())],
            check=True, capture_output=True, timeout=120,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    out = outdir / f"{filepath.stem}.{target}"
    if not out.exists():
        raise RuntimeError(f"LibreOffice failed to convert {filepath.name}")
    return out


def _extract_converted(filepath: Path, file_type: str) -> ExtractedDocument:
    try:
        converted = _convert_with_libreoffice(filepath)
    except Exception as lo_error:
        fallback = {"rtf": extract_rtf, "odt": extract_odt, "doc": _extract_doc_cli}.get(file_type)
        if fallback is None:
            raise
        try:
            return fallback(filepath)
        except Exception as e:
            raise RuntimeError(f"{lo_error}; fallback reader failed: {e}") from e
    try:
        doc = extract_docx(converted, file_type=file_type)
    finally:
        shutil.rmtree(converted.parent, ignore_errors=True)
    doc.source_path = str(filepath)
    return doc


def _doc_from_plain(text: str, source: str, file_type: str, lines: list | None = None) -> ExtractedDocument:
    rows = _rows_from_plain_lines(lines if lines is not None else [(l, False) for l in text.splitlines()])
    layout_text, raw_text, blocks = _render(rows)
    return ExtractedDocument(raw_text=raw_text, blocks=blocks, layout_text=layout_text,
                             tables=[], source_path=source, file_type=file_type)


def _extract_doc_cli(filepath: Path) -> ExtractedDocument:
    """Legacy .doc without LibreOffice: antiword or catdoc if installed."""
    for tool, args in (("antiword", ["-w", "0"]), ("catdoc", ["-w"])):
        exe = shutil.which(tool)
        if exe:
            res = subprocess.run([exe, *args, str(filepath)], capture_output=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                return _doc_from_plain(res.stdout.decode("utf-8", errors="replace"), str(filepath), "doc")
    raise RuntimeError("no .doc reader available (install LibreOffice, antiword or catdoc)")


# --- ODT (OpenDocument): content.xml inside a zip -------------------------
_ODF_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
_ODF_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


def extract_odt(filepath: str | Path) -> ExtractedDocument:
    import zipfile
    from xml.etree import ElementTree as ET

    with zipfile.ZipFile(str(filepath)) as z:
        root = ET.fromstring(z.read("content.xml"))

    def inline(el) -> str:
        parts = [el.text or ""]
        for ch in el:
            tag = ch.tag
            if tag == f"{_ODF_TEXT}s":
                parts.append(" " * int(ch.get(f"{_ODF_TEXT}c", "1")))
            elif tag == f"{_ODF_TEXT}tab":
                parts.append(" | ")
            elif tag == f"{_ODF_TEXT}line-break":
                parts.append("\n")
            elif tag not in (f"{_ODF_TEXT}note",):
                parts.append(inline(ch))
            parts.append(ch.tail or "")
        return "".join(parts)

    lines: list[tuple[str, bool]] = []

    def walk(el, bullet=False):
        for ch in el:
            tag = ch.tag
            if tag in (f"{_ODF_TEXT}p", f"{_ODF_TEXT}h"):
                for piece in inline(ch).split("\n"):
                    lines.append((("• " if bullet else "") + piece, tag == f"{_ODF_TEXT}h"))
                if tag == f"{_ODF_TEXT}h":
                    lines.append(("", False))
            elif tag == f"{_ODF_TEXT}list-item":
                walk(ch, bullet=True)
            elif tag == f"{_ODF_TABLE}table-row":
                cells = []
                for cell in ch:
                    if cell.tag == f"{_ODF_TABLE}table-cell":
                        cells.append(" ".join(inline(p) for p in cell.iter(f"{_ODF_TEXT}p")).strip())
                if any(cells):
                    lines.append((" | ".join(c for c in cells if c), False))
            else:
                walk(ch, bullet)

    walk(root)
    return _doc_from_plain("", str(filepath), "odt", lines=lines)


# --- RTF: small control-word stripper ------------------------------------
_RTF_TOKEN_RE = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z])|([{}])|[\r\n]+|([^\\{}\r\n]+)")
_RTF_SKIP_DESTINATIONS = {
    "fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "header", "footer",
    "headerl", "headerr", "footerl", "footerr", "listtable", "listoverridetable",
    "rsidtbl", "themedata", "colorschememapping", "latentstyles", "datastore", "xmlnstbl",
    "generator", "fldinst", "filetbl", "revtbl", "pgdsctbl",
}


def rtf_to_text(rtf: str) -> str:
    stack: list[tuple[bool, int]] = []
    skip = False
    uc_skip = 1
    pending_skip = 0
    codepage = "cp1252"
    out: list[str] = []
    for m in _RTF_TOKEN_RE.finditer(rtf):
        word, arg, hexchar, sym, brace, text = m.groups()
        if brace == "{":
            stack.append((skip, uc_skip))
        elif brace == "}":
            skip, uc_skip = stack.pop() if stack else (False, 1)
        elif sym:
            if sym == "*":
                skip = True
            elif sym in "\\{}" and not skip:
                out.append(sym)
            elif sym == "~" and not skip:
                out.append(" ")
        elif word:
            if word in _RTF_SKIP_DESTINATIONS:
                skip = True
            elif word == "ansicpg" and arg:
                codepage = f"cp{arg}"
            elif word == "uc" and arg:
                uc_skip = int(arg)
            elif skip:
                continue
            elif word in ("par", "line", "row", "sect", "page"):
                out.append("\n")
            elif word == "tab":
                out.append(" | ")
            elif word == "cell":
                out.append(" | ")
            elif word == "u" and arg:
                code = int(arg)
                out.append(chr(code + 65536 if code < 0 else code))
                pending_skip = uc_skip
        elif hexchar:
            if pending_skip:
                pending_skip -= 1
            elif not skip:
                try:
                    out.append(bytes([int(hexchar, 16)]).decode(codepage))
                except (UnicodeDecodeError, LookupError):
                    pass
        elif text and not skip:
            if pending_skip:
                text = text[pending_skip:]
                pending_skip = 0
            out.append(text)
    text = "".join(out)
    return re.sub(r"(\s*\|\s*)+\n", "\n", text)


def extract_rtf(filepath: str | Path) -> ExtractedDocument:
    raw = Path(filepath).read_bytes().decode("latin-1")
    return _doc_from_plain(rtf_to_text(raw), str(filepath), "rtf")


def _read_text_file(filepath: Path) -> str:
    data = filepath.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1258", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _rows_from_plain_lines(lines: list[tuple[str, bool]]) -> list[_Row]:
    rows: list[_Row] = []
    blank = False
    for text, is_heading_tag in lines:
        line = clean_line(text)
        if not line or is_noise(line):
            blank = True
            continue
        md = re.match(r"^#{1,6}\s+(.*)", line)
        if md:
            line, is_heading_tag = md.group(1).strip(), True
        rows.append(_Row(text=line, style_heading=is_heading_tag, bold=is_heading_tag,
                         size=14.0 if is_heading_tag else 11.0, para_break=blank,
                         y0=float(len(rows)), y1=float(len(rows) + 1)))
        blank = False
    return rows


def extract_text_file(filepath: str | Path) -> ExtractedDocument:
    filepath = Path(filepath)
    text = _read_text_file(filepath)
    rows = _rows_from_plain_lines([(l, False) for l in text.splitlines()])
    layout_text, raw_text, blocks = _render(rows)
    return ExtractedDocument(raw_text=raw_text, blocks=blocks, layout_text=layout_text,
                             tables=[], source_path=str(filepath), file_type="text")


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "header", "footer",
             "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "dt", "dd"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[tuple[str, bool]] = []
        self.buf: list[str] = []
        self.heading = False
        self.skip = 0
        self.links: list[str] = []

    def _flush(self):
        text = "".join(self.buf).strip()
        if text:
            self.lines.append((text, self.heading))
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag in ("td", "th"):
            self.buf.append(" | ")
        if tag == "li":
            self._flush()
            self.buf.append("• ")
            return
        if tag in self.BLOCK:
            self._flush()
            self.heading = tag in ("h1", "h2", "h3", "h4", "h5", "h6")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
        if tag in self.BLOCK:
            self._flush()
            self.heading = False

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data.replace("\n", " "))


def extract_html(filepath: str | Path) -> ExtractedDocument:
    filepath = Path(filepath)
    parser = _HTMLText()
    parser.feed(_read_text_file(filepath))
    parser._flush()
    lines = [(re.sub(r"^\s*\|\s*", "", html.unescape(t)), h) for t, h in parser.lines]
    rows = _rows_from_plain_lines(lines)
    layout_text, raw_text, blocks = _render(rows)
    return ExtractedDocument(raw_text=raw_text, blocks=blocks, layout_text=layout_text,
                             tables=[], source_path=str(filepath),
                             links=_dedupe_links(parser.links), file_type="html")


def extract(filepath: str | Path) -> ExtractedDocument:
    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(filepath)
    if ext == ".docx":
        try:
            return extract_docx(filepath)
        except Exception:
            # mislabeled .doc / broken package: let LibreOffice repair it
            return _extract_converted(filepath, "docx")
    if ext == ".odt":
        return extract_odt(filepath)
    if ext in (".doc", ".rtf"):
        return _extract_converted(filepath, ext[1:])
    if ext in (".txt", ".md"):
        return extract_text_file(filepath)
    if ext in (".html", ".htm"):
        return extract_html(filepath)
    if ext in IMAGE_EXTENSIONS:
        return extract_image(filepath)
    raise ValueError(f"Unsupported file format: {ext}")


def extract_key_value_pairs(doc: ExtractedDocument) -> dict[str, str]:
    """
    Extract "label: value" pairs from the document (used by the rule-based
    extractor and as hints). Handles "Label: value", "Label | value" rows and
    2/4-cell table rows.
    """
    pairs: dict[str, str] = {}
    lines = [b.text for b in doc.blocks]
    for idx, line in enumerate(lines):
        if is_form_label(line) or is_noise(line):
            continue
        segments = [s.strip() for s in line.split(" | ")] if " | " in line else [line]
        for seg_i, seg in enumerate(segments):
            if ":" in seg:
                key, val = (p.strip() for p in seg.split(":", 1))
                if not key or len(key) >= 60 or is_form_label(key) or is_noise(key):
                    continue
                if key.lower() in ("http", "https"):
                    continue
                if val:
                    pairs[key] = val
                elif seg_i + 1 < len(segments):
                    pairs[key] = segments[seg_i + 1]
                elif idx + 1 < len(lines) and not is_form_label(lines[idx + 1]):
                    nxt = lines[idx + 1]
                    if ":" not in nxt and len(nxt) < 120:
                        pairs[key] = nxt

    for table in doc.tables:
        for row in table:
            cleaned = [c for c in row if c and not is_noise(c) and not is_form_label(c)]
            if len(cleaned) == 2 and len(cleaned[0]) < 60:
                pairs[cleaned[0].rstrip(":")] = cleaned[1]
            elif len(cleaned) == 4:
                if len(cleaned[0]) < 60:
                    pairs[cleaned[0].rstrip(":")] = cleaned[1]
                if len(cleaned[2]) < 60:
                    pairs[cleaned[2].rstrip(":")] = cleaned[3]
    return pairs


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        doc = extract(sys.argv[1])
        print(f"=== Source: {doc.source_path} ({doc.file_type}, {doc.page_count} pages"
              f"{', OCR' if doc.ocr_used else ''}) ===")
        print(f"Rows: {len(doc.blocks)}  Tables: {len(doc.tables)}  Links: {doc.links}")
        for w in doc.warnings:
            print(f"WARNING: {w}")
        print("\n=== Layout Text ===")
        print(doc.layout_text)
    else:
        print("Usage: python text_extractor.py <cv file>")
