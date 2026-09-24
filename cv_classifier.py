"""
Classifies CV documents as either 'free_form' or 'structured_form'.
Routes to different extraction strategies based on the classification.
"""
import re
from dataclasses import dataclass
from text_extractor import ExtractedDocument, TextBlock


@dataclass
class CVClassification:
    cv_type: str  # "free_form" or "structured_form"
    confidence: float
    signals: dict[str, float]  # individual signal scores


# Known form/template keywords
FORM_KEYWORDS = [
    "các thông tin bắt buộc",
    "required information",
    "page 1 of",
    "page 2 of",
    "trang 1",
    "i accept the",
    "i commit not to",
    "position_w",
    "name of company",
    "tên đơn vị công tác",
    "lý do thôi việc",
    "bạn biết thông tin tuyển dụng",
    "giải thích cho vị trí",
    "chi tiết về kinh nghiệm",
]

# Picklist ID pattern: 5-digit numbers commonly found in structured forms
REGEX_PICKLIST_ID = re.compile(r"\b1\d{4}\b")


def classify(doc: ExtractedDocument) -> CVClassification:
    """
    Classify a CV document based on structural signals.
    Returns classification with type, confidence, and individual signal scores.
    """
    signals: dict[str, float] = {}

    # Signal 1: Table density
    total_table_cells = 0
    for table in doc.tables:
        for row in table:
            total_table_cells += len(row)
    # Structured forms have lots of table cells (50+)
    signals["table_density"] = min(total_table_cells / 100.0, 1.0)

    # Signal 2: Asterisk count (form labels use *)
    asterisk_count = doc.raw_text.count("*")
    signals["asterisk_labels"] = min(asterisk_count / 10.0, 1.0)

    # Signal 3: Form keywords presence
    text_lower = doc.raw_text.lower()
    form_kw_hits = sum(1 for kw in FORM_KEYWORDS if kw in text_lower)
    signals["form_keywords"] = min(form_kw_hits / 3.0, 1.0)

    # Signal 4: Font size variance (free-form has big names, varied sizes)
    font_sizes = set()
    for b in doc.blocks:
        if b.font_size > 0:
            font_sizes.add(round(b.font_size, 1))
    if font_sizes:
        variance = max(font_sizes) - min(font_sizes)
        # High variance = likely free-form (big name + small body)
        signals["font_variance"] = max(0, 1.0 - variance / 10.0)
    else:
        signals["font_variance"] = 0.5

    # Signal 5: Embedded picklist IDs (structured forms embed option IDs)
    picklist_ids = REGEX_PICKLIST_ID.findall(doc.raw_text)
    signals["picklist_ids"] = min(len(picklist_ids) / 5.0, 1.0)

    # Signal 6: Multi-page (forms are often 2-3 pages with repeated structure)
    pages = set(b.page for b in doc.blocks)
    tables_per_page = len(doc.tables) / max(len(pages), 1)
    signals["multi_page_tables"] = min(tables_per_page / 2.0, 1.0)

    # Weighted score: higher = more likely structured form
    weights = {
        "table_density": 0.25,
        "asterisk_labels": 0.20,
        "form_keywords": 0.25,
        "font_variance": 0.10,
        "picklist_ids": 0.10,
        "multi_page_tables": 0.10,
    }
    form_score = sum(signals[k] * weights[k] for k in weights)

    if form_score >= 0.35:
        cv_type = "structured_form"
        confidence = min(form_score / 0.5, 1.0)
    else:
        cv_type = "free_form"
        confidence = min((1.0 - form_score) / 0.5, 1.0)

    return CVClassification(
        cv_type=cv_type,
        confidence=round(confidence, 2),
        signals={k: round(v, 3) for k, v in signals.items()},
    )


if __name__ == "__main__":
    import sys
    from text_extractor import extract

    if len(sys.argv) > 1:
        doc = extract(sys.argv[1])
        result = classify(doc)
        print(f"Type: {result.cv_type} (confidence: {result.confidence})")
        print("Signals:")
        for k, v in result.signals.items():
            print(f"  {k}: {v}")
    else:
        print("Usage: python cv_classifier.py <file.pdf|file.docx>")
