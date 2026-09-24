"""
Rule-based field extraction from CV text.
Uses regex patterns, keyword matching, section detection, NER, and
Vietnamese-specific heuristics to extract all candidate profile fields.

Handles both free-form CVs and structured HR application forms.
"""
import re
from dataclasses import dataclass, field
from text_extractor import ExtractedDocument, TextBlock, extract_key_value_pairs, is_noise, is_form_label
from text_utils import strip_diacritics, normalize_label

# ---------------------------------------------------------------------------
# Label aliases: maps field labels (Vietnamese & English variants) to field_id
# ---------------------------------------------------------------------------

LABEL_ALIASES: dict[str, list[str]] = {
    "fullName": [
        "ho va ten", "họ và tên", "ho ten", "họ tên",
        "full name", "name",
        "ho va ten / full name", "họ và tên / full name",
        "candidate name", "applicant name",
    ],
    "dateOfBirth": [
        "ngay sinh", "ngày sinh", "date of birth", "dob",
        "sinh ngay", "sinh ngày", "birthday", "born",
        "ngay sinh / dob", "ngày sinh / dob",
        "ngay thang nam sinh", "ngày tháng năm sinh",
    ],
    "cellPhone": [
        "so dien thoai", "số điện thoại", "dien thoai", "điện thoại",
        "phone", "mobile", "cell", "tel", "sdt", "sđt",
        "mobile phone", "phone number", "contact number",
        "so dt", "số đt",
    ],
    "primaryEmail": [
        "email", "e-mail", "thu dien tu", "thư điện tử",
        "dia chi email", "địa chỉ email", "email address",
    ],
    "contactEmail": [
        "email lien he", "email liên hệ", "contact email",
    ],
    "address": [
        "dia chi", "địa chỉ", "address", "noi o", "nơi ở",
        "dia chi thuong tru", "địa chỉ thường trú",
        "dia chi hien tai", "địa chỉ hiện tại",
        "dia chi lien he", "địa chỉ liên hệ",
        "current address", "permanent address",
    ],
    "idCard": [
        "cmnd", "cccd", "cmnd/cccd", "so cmnd", "số cmnd",
        "so cccd", "số cccd", "chung minh nhan dan",
        "chứng minh nhân dân", "can cuoc cong dan",
        "căn cước công dân", "id card", "id number",
        "passport", "ho chieu", "hộ chiếu",
        "personal id", "passport number",
        "so cmnd / cccd", "cmtnd",
    ],
    "idIssuePlace": [
        "noi cap", "nơi cấp", "place of issue", "issued at",
        "noi cap cmnd", "co quan cap", "cơ quan cấp",
    ],
    "idIssueDt": [
        "ngay cap", "ngày cấp", "issue date", "date of issue",
        "ngay cap cmnd", "cap ngay", "cấp ngày",
    ],
    "zip": [
        "ma buu chinh", "mã bưu chính", "postal code", "zip code", "zip",
    ],
    "middleName": [
        "ten dem", "tên đệm", "middle name",
    ],
    "firstName": [
        "ho", "họ", "first name", "family name", "surname",
    ],
    "lastName": [
        "ten", "tên", "last name", "given name",
    ],
    # --- Sections ---
    "_section_education": [
        "hoc van", "học vấn", "trinh do hoc van", "trình độ học vấn",
        "education", "educational background", "academic background",
        "bang cap", "bằng cấp", "qua trinh hoc tap", "quá trình học tập",
        "dao tao", "đào tạo",
    ],
    "_section_experience": [
        "kinh nghiem lam viec", "kinh nghiệm làm việc",
        "kinh nghiem", "kinh nghiệm", "work experience",
        "professional experience", "employment history",
        "qua trinh lam viec", "quá trình làm việc",
        "qua trinh cong tac", "quá trình công tác",
        "experience", "career history",
    ],
    "_section_languages": [
        "ngoai ngu", "ngoại ngữ", "ngon ngu", "ngôn ngữ",
        "languages", "language skills", "foreign languages",
        "trinh do ngoai ngu", "trình độ ngoại ngữ",
    ],
    "_section_certificates": [
        "chung chi", "chứng chỉ", "chung nhan", "chứng nhận",
        "certificates", "certifications", "licenses",
        "bang cap chung chi", "bằng cấp chứng chỉ",
    ],
    "_section_awards": [
        "giai thuong", "giải thưởng", "khen thuong", "khen thưởng",
        "awards", "honors", "awards and achievements", "recognition",
    ],
    "_section_courses": [
        "khoa hoc", "khóa học", "courses", "training",
        "dao tao ngan han", "đào tạo ngắn hạn",
    ],
    "_section_family": [
        "gia dinh", "gia đình", "than nhan", "thân nhân",
        "family", "family members", "dependents",
        "nguoi than", "người thân",
    ],
    "_section_skills": [
        "ky nang", "kỹ năng", "skills", "technical skills",
        "ky nang tin hoc", "kỹ năng tin học", "computer skills",
    ],
    "_section_projects": [
        "projects", "du an", "dự án",
        "academic projects", "personal projects", "notable projects",
    ],
}

_LABEL_TO_FIELD: dict[str, str] = {}
_LABEL_TO_FIELD_NORMALIZED: dict[str, str] = {}
for field_id, aliases in LABEL_ALIASES.items():
    for alias in aliases:
        _LABEL_TO_FIELD[alias.lower()] = field_id
        _LABEL_TO_FIELD_NORMALIZED[normalize_label(alias)] = field_id


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

REGEX_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
# Vietnamese phone: +84 (with optional parens) or 0 prefix, then 9-10 digits
REGEX_PHONE_VN = re.compile(
    r"(?<![a-zA-Z\d])"
    r"(?:\(?\+?84\)?[\s.\-]*|0)"
    r"(?:[\s.\-]*\d){9,10}"
    r"(?!\d)"
)
# International phone: +CC prefix followed by digits with separators
REGEX_PHONE_INTL = re.compile(
    r"(?<![a-zA-Z\d])"
    r"\(?\+\d{1,3}\)?[\s.\-]*"
    r"(?:\(?\d{1,4}\)?[\s.\-]*)?"
    r"\d(?:[\s.\-]*\d){5,11}"
    r"(?!\d)"
)
_BULLET_RE = re.compile(r"^[-•●○*+>]\s")
_NUMBERED_RE = re.compile(r"^\d{1,2}[.)]\s")
REGEX_DATE = re.compile(
    r"(?:"
    r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
    r"|"
    r"\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}"
    r"|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}[\s,]+\d{4}"
    r"|"
    r"\d{1,2}[\s,]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4}"
    r"|"
    r"(?:thang|tháng)\s+\d{1,2}[/\-,\s]+(?:nam|năm)\s+\d{4}"
    r"|"
    r"T\d{1,2}/\d{4}"  # T7/2022 (Vietnamese month shorthand)
    r"|"
    r"\d{1,2}/\d{4}"
    r")",
    re.IGNORECASE,
)
# Vietnamese ID: exactly 9 or 12 digits, NOT starting with 0 (phones start with 0)
REGEX_VN_ID = re.compile(r"\b([1-9]\d{8}|[0-9]\d{11})\b")
REGEX_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4}|(?:nay|present|current|hien tai|hiện tại))", re.IGNORECASE)
# T7/2022 - T5/2024 style
REGEX_VN_MONTH_RANGE = re.compile(r"T(\d{1,2})/(\d{4})\s*[-–—]\s*T(\d{1,2})/(\d{4})", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Blacklists for name detection
# ---------------------------------------------------------------------------

NAME_BLACKLIST_PHRASES = {
    "các thông tin", "thông tin bắt buộc", "required information",
    "thông tin cá nhân", "personal information", "personal details",
    "mục tiêu", "objective", "tóm tắt", "summary",
    "kinh nghiệm", "experience", "học vấn", "education",
    "kỹ năng", "skills", "ngôn ngữ", "languages",
    "chứng chỉ", "certificates", "giải thưởng", "awards",
    "bằng xuất sắc", "bằng giỏi", "bằng khá",
    "curriculum vitae", "resume", "profile",
    "ứng viên", "candidate", "applicant",
    "quá trình", "công tác", "đào tạo",
    "page ", "trang ",
    "about me", "about us", "giới thiệu",
    "contact", "liên hệ", "lien he",
    "work experience", "professional",
    "hoàn thành", "hoan thanh",
    "application", "transfer", "internal",
    "đơn xin", "ứng tuyển", "chuyển đổi",
}

NAME_ORG_WORDS = {
    "bank", "corporation", "company", "limited", "joint stock",
    "commercial", "jsc", "llc", "ltd", "inc.", "corp",
    "ngan hang", "cong ty", "tnhh", "co phan", "thuong mai",
}

HONORIFIC_RE = re.compile(r"^(Dr|Mr|Ms|Mrs|Prof|TS|ThS|PGS|GS)\.?\s+", re.IGNORECASE)

LANGUAGE_NON_NAMES = {
    "reading", "writing", "speaking", "listening",
    "doc", "viet", "noi", "nghe",
    "native", "basic", "intermediate", "advanced",
    "fluent", "beginner", "excellent", "good", "fair", "poor",
    "date", "applicant signature", "signature",
    "approved", "pending", "signature / date",
}

PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "go", "rust", "c", "c++",
    "c#", "ruby", "php", "swift", "kotlin", "scala", "perl", "r", "matlab",
    "sql", "html", "css", "bash", "shell", "dart", "lua", "haskell",
    "objective-c", "groovy", "clojure", "elixir", "vba", "sas",
    "react", "angular", "vue", "node.js", "express", "django", "flask",
    "spring", "laravel", "rails", "next.js",
}

EXP_NON_ENTRIES = {
    "job reference", "expected salary", "willing to relocate",
    "available from", "notice period", "start date",
    "desired position", "salary expectation", "references",
}

CERT_HEADER_NAMES = {
    "issuer", "year", "name", "date", "status", "no", "stt",
    "certificate id", "credential id",
}

# ---------------------------------------------------------------------------
# Vietnamese name parsing
# ---------------------------------------------------------------------------

VN_FAMILY_NAMES = {
    "nguyen", "nguyễn", "tran", "trần", "le", "lê", "pham", "phạm",
    "huynh", "huỳnh", "hoang", "hoàng", "phan", "vũ", "vu", "võ", "vo",
    "dang", "đặng", "bui", "bùi", "do", "đỗ", "ho", "hồ", "ngo", "ngô",
    "duong", "dương", "ly", "lý", "luong", "lương", "truong", "trương",
    "ha", "hà", "dao", "đào", "mai", "tang", "tăng", "dinh", "đinh",
    "lam", "lâm", "trinh", "trịnh", "doan", "đoàn", "cao", "ta", "tạ",
    "nghiem", "nghiêm", "vuong", "vương", "chau", "châu", "quach", "quách",
    "tong", "tống", "la", "lã", "phung", "phùng", "thai", "thái",
}


@dataclass
class ParsedName:
    full_name: str
    first_name: str
    middle_name: str
    last_name: str


def _is_valid_name(text: str) -> bool:
    """Check if text looks like a person's name, not a form label or noise."""
    text_lower = strip_diacritics(text.lower())
    # Must not contain blacklisted phrases
    for phrase in NAME_BLACKLIST_PHRASES:
        if strip_diacritics(phrase) in text_lower:
            return False
    # Must not contain organization name indicators
    for phrase in NAME_ORG_WORDS:
        if strip_diacritics(phrase) in text_lower:
            return False
    # Must not contain special chars that indicate form content
    if any(c in text for c in "@*#{}[]()=+<>"):
        return False
    # Must not be a URL or email
    if REGEX_EMAIL.search(text):
        return False
    # Must have 2-6 words (names)
    words = text.strip().split()
    if len(words) < 2 or len(words) > 6:
        return False
    # Each word should be short (name parts, not sentences)
    if any(len(w) > 15 for w in words):
        return False
    # At least one word should look like a Vietnamese or common name part (all alpha)
    alpha_words = [w for w in words if w.isalpha()]
    if len(alpha_words) < 2:
        return False
    # Reject if most words are single letters (e.g. "A B OU T ME")
    single_letter_count = sum(1 for w in words if len(w) == 1)
    if single_letter_count >= 2:
        return False
    # Each word should be at least 2 chars (real name parts)
    short_words = [w for w in words if len(w) < 2]
    if len(short_words) > 1:
        return False
    return True


def _looks_like_vn_name(text: str) -> bool:
    """Check if text starts with a known Vietnamese family name."""
    words = text.strip().split()
    if not words:
        return False
    first = strip_diacritics(words[0])
    return first in VN_FAMILY_NAMES


def parse_vietnamese_name(name_str: str) -> ParsedName:
    cleaned = HONORIFIC_RE.sub("", name_str.strip())
    parts = cleaned.split()
    if not parts:
        return ParsedName(cleaned, "", "", "")

    if len(parts) == 1:
        return ParsedName(cleaned, parts[0], "", parts[0])

    if len(parts) == 2:
        return ParsedName(cleaned, parts[0], "", parts[1])

    # firstName = first word, middleName = middle words, lastName = last word
    return ParsedName(
        full_name=cleaned,
        first_name=parts[0],
        middle_name=" ".join(parts[1:-1]),
        last_name=parts[-1],
    )


def _normalize_name_case(name: str) -> str:
    """Convert ALL CAPS names to title case."""
    if name == name.upper() and any(c.isalpha() for c in name):
        return name.title()
    return name


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

@dataclass
class Section:
    name: str
    start_idx: int
    end_idx: int
    text: str
    blocks: list[TextBlock] = field(default_factory=list)


def detect_sections(doc: ExtractedDocument) -> list[Section]:
    lines = doc.layout_text.split("\n")
    section_starts: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue

        is_header = line_clean.startswith("[SECTION]")
        if is_header:
            line_clean = line_clean.replace("[SECTION]", "").strip()

        # Skip very long lines — section headers are short
        if len(line_clean.split()) > 8:
            continue

        check_text = normalize_label(line_clean)
        if not check_text:
            continue

        for alias_norm, field_id in _LABEL_TO_FIELD_NORMALIZED.items():
            if not field_id.startswith("_section_"):
                continue

            if (
                alias_norm == check_text
                or (is_header and len(check_text.split()) <= 6 and alias_norm in check_text)
                or (len(check_text.split()) <= 4 and alias_norm == check_text)
            ):
                section_type = field_id.replace("_section_", "")
                section_starts.append((i, section_type))
                break

    section_header_lines = {s[0] for s in section_starts}
    _INCLUDE_BOLD_SECTIONS = {"experience", "education"}

    sections = []
    for idx, (start, stype) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
        include_bold = stype in _INCLUDE_BOLD_SECTIONS
        section_lines = []
        for li in range(start + 1, end):
            stripped = lines[li].strip()
            if stripped.startswith("[SECTION]"):
                if not include_bold or li in section_header_lines:
                    continue
                inner = stripped.replace("[SECTION]", "").strip()
                if inner:
                    section_lines.append(inner)
                continue
            if is_noise(stripped) or is_form_label(stripped):
                continue
            section_lines.append(stripped)
        section_text = "\n".join(section_lines)
        sections.append(Section(name=stype, start_idx=start, end_idx=end, text=section_text))

    return sections


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

@dataclass
class ExtractedFields:
    personal: dict[str, str] = field(default_factory=dict)
    education: list[dict[str, str]] = field(default_factory=list)
    experience: list[dict[str, str]] = field(default_factory=list)
    languages: list[dict[str, str]] = field(default_factory=list)
    certificates: list[dict[str, str]] = field(default_factory=list)
    awards: list[dict[str, str]] = field(default_factory=list)
    courses: list[dict[str, str]] = field(default_factory=list)
    family: list[dict[str, str]] = field(default_factory=list)
    disciplinary: list[dict[str, str]] = field(default_factory=list)
    raw_kv: dict[str, str] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)


def extract_fields(doc: ExtractedDocument, cv_type: str = "free_form") -> ExtractedFields:
    result = ExtractedFields()
    full_text = doc.raw_text

    # Step 1: Extract key-value pairs (filtered)
    kv_pairs = extract_key_value_pairs(doc)
    result.raw_kv = kv_pairs

    # Step 2: Match KV pairs to field IDs via label aliases
    _match_kv_to_fields(kv_pairs, result)

    # Step 3: Regex extraction for specific patterns
    _extract_by_regex(full_text, result)

    # Table extraction first (especially useful for structured forms)
    _extract_from_tables(doc, result)

    # Section-based extraction (for both types — noise filters handle form garbage)
    result.sections = detect_sections(doc)
    for section in result.sections:
        if section.name == "education":
            result.education = result.education or _parse_education_section(section, result)
        elif section.name == "experience":
            result.experience = result.experience or _parse_experience_section(section)
        elif section.name == "languages":
            result.languages = result.languages or _parse_language_section(section)
        elif section.name == "certificates":
            result.certificates = result.certificates or _parse_certificate_section(section)
        elif section.name == "awards":
            result.awards = result.awards or _parse_awards_section(section)
        elif section.name == "courses":
            result.courses = result.courses or _parse_courses_section(section)
        elif section.name == "family":
            result.family = result.family or _parse_family_section(section)

    # Inline language parsing from KV pairs (e.g., "Languages: English (Native), Spanish (B2)")
    if not result.languages:
        result.languages = _parse_inline_languages(kv_pairs)

    # Name: always derive components from fullName (most reliable source)
    if "fullName" in result.personal:
        result.personal["fullName"] = _normalize_name_case(result.personal["fullName"])
        parsed = parse_vietnamese_name(result.personal["fullName"])
        result.personal["fullName"] = parsed.full_name
        result.personal["firstName"] = parsed.first_name
        result.personal["lastName"] = parsed.last_name
        if parsed.middle_name:
            result.personal["middleName"] = parsed.middle_name

    # Fill contactEmail from primaryEmail if missing
    if "primaryEmail" in result.personal and "contactEmail" not in result.personal:
        result.personal["contactEmail"] = result.personal["primaryEmail"]

    # Name fallbacks: bold text heuristic, then NER
    if "fullName" not in result.personal:
        _extract_name_from_prominent_text(doc, result)
    if "fullName" not in result.personal:
        _ner_extract_name(doc, result)

    # Normalize name case for fallback-extracted names too
    if "fullName" in result.personal:
        for key in ("fullName", "firstName", "lastName", "middleName"):
            if key in result.personal:
                result.personal[key] = _normalize_name_case(result.personal[key])

    # Step 10: Validate and clean extracted values
    _validate_fields(result)

    return result


def _match_kv_to_fields(kv_pairs: dict[str, str], result: ExtractedFields):
    for label, value in kv_pairs.items():
        if is_form_label(label) or is_noise(value):
            continue

        label_norm = normalize_label(label)
        if not label_norm:
            continue

        # Exact match against pre-computed normalized table
        exact = _LABEL_TO_FIELD_NORMALIZED.get(label_norm)
        if exact and not exact.startswith("_section_") and exact not in result.personal:
            result.personal[exact] = value
            result.confidence[exact] = 1.0
            continue

        # Fuzzy: substring or word-subset match
        best_match = None
        best_score = 0.0

        for alias_norm, field_id in _LABEL_TO_FIELD_NORMALIZED.items():
            if field_id.startswith("_section_"):
                continue

            if alias_norm in label_norm or label_norm in alias_norm:
                score = len(alias_norm) / max(len(label_norm), 1)
                if score > best_score and score > 0.5:
                    best_match = field_id
                    best_score = score

            alias_words = set(alias_norm.split())
            label_words = set(label_norm.split())
            if alias_words and alias_words.issubset(label_words):
                score = len(alias_words) / max(len(label_words), 1)
                if score > best_score and score > 0.5:
                    best_match = field_id
                    best_score = score

        if best_match and best_match not in result.personal:
            result.personal[best_match] = value
            result.confidence[best_match] = best_score


def _extract_by_regex(text: str, result: ExtractedFields):
    # Email — find all, pick the first one that looks personal (not @company domain)
    if "primaryEmail" not in result.personal:
        emails = REGEX_EMAIL.findall(text)
        if emails:
            result.personal["primaryEmail"] = emails[0]
            result.confidence["primaryEmail"] = 0.8

    # Phone — try VN format first, then international
    if "cellPhone" not in result.personal:
        phones = REGEX_PHONE_VN.findall(text)
        if not phones:
            phones = REGEX_PHONE_INTL.findall(text)
        if phones:
            phone = phones[0].strip()
            digits_only = re.sub(r"[^\d]", "", phone)
            if 7 <= len(digits_only) <= 15:
                result.personal["cellPhone"] = phone
                result.confidence["cellPhone"] = 0.8

    # ID number — Vietnamese CCCD (12 digits) or old CMND (9 digits), NOT starting with 0
    if "idCard" not in result.personal:
        phone_val = result.personal.get("cellPhone", "").replace(" ", "")
        ids = REGEX_VN_ID.findall(text)
        for candidate_id in ids:
            if candidate_id == phone_val:
                continue
            # Skip if it's a phone number pattern (starts with 0 and is 10 digits)
            if candidate_id.startswith("0") and len(candidate_id) == 10:
                continue
            result.personal["idCard"] = candidate_id
            result.confidence["idCard"] = 0.6
            break


def _extract_from_tables(doc: ExtractedDocument, result: ExtractedFields):
    """
    Extract structured data from form tables.
    Handles multi-column tables where first row is headers.
    """
    last_lang_col_count = 0

    for table in doc.tables:
        if len(table) < 1:
            continue

        header_row = table[0]

        # Skip KV-style tables where cells contain colons (not column headers)
        colon_cells = sum(1 for c in header_row if c and ":" in c)
        if colon_cells >= 2:
            continue

        # Single-row table could be continuation of previous language table
        if len(table) == 1 and last_lang_col_count > 0 and len(header_row) == last_lang_col_count:
            lang_val = header_row[0].strip() if header_row[0] else ""
            if lang_val and lang_val.lower() not in LANGUAGE_NON_NAMES:
                entry: dict[str, str] = {"language": lang_val}
                cert_val = header_row[-1].strip() if header_row[-1] else ""
                if cert_val and cert_val.lower() not in LANGUAGE_NON_NAMES and cert_val != lang_val:
                    entry["remark"] = cert_val
                result.languages.append(entry)
            continue

        if len(table) < 2:
            continue

        header_text = " ".join(c.lower() for c in header_row if c)
        header_stripped = strip_diacritics(header_text)

        # Work experience table detection
        if any(kw in header_stripped for kw in [
            "ten don vi cong tac", "name of company", "chuc vu",
            "position", "company", "employer", "department",
        ]):
            _parse_experience_table(table, result)
            continue

        # Education table
        if any(kw in header_stripped for kw in [
            "truong", "school", "university", "bang cap",
            "degree", "institution", "field of study",
        ]):
            _parse_education_table(table, result)
            continue

        # Language table (check before certificate — language tables may have a "Certificate" column)
        if any(kw in header_stripped for kw in [
            "language", "ngoai ngu", "ngon ngu",
        ]):
            _parse_language_table(table, result)
            last_lang_col_count = len(header_row)
            continue

        # Certificate table
        if any(kw in header_stripped for kw in [
            "certification", "certificate", "chung chi", "chung nhan",
        ]):
            _parse_certificate_table(table, result)
            continue


def _parse_experience_table(table: list[list[str]], result: ExtractedFields):
    """Parse a structured work experience table from HR forms."""
    if result.experience:
        return

    header = [strip_diacritics(c) for c in table[0]]

    from_col = to_col = company_col = position_col = period_col = -1
    for i, h in enumerate(header):
        h_clean = re.sub(r"[^a-z0-9\s]", "", h).strip()
        if h_clean in ("tu", "from"):
            from_col = i
        elif h_clean in ("toi", "to", "den"):
            to_col = i
        elif h_clean in ("period", "thoi gian"):
            period_col = i
        elif any(kw in h_clean for kw in [
            "ten don vi", "name of company", "company",
            "employer", "department", "institution", "organization",
        ]):
            company_col = i
        elif any(kw in h_clean for kw in [
            "chuc vu", "position", "title", "vi tri",
        ]):
            position_col = i

    max_col = max(from_col, to_col, company_col, position_col, period_col)
    for row in table[1:]:
        if len(row) <= max_col:
            continue
        exp: dict[str, str] = {}

        # Handle combined "Period" column (e.g., "Jul 2021 — Present")
        if period_col >= 0 and row[period_col] and not is_form_label(row[period_col]):
            period = row[period_col].strip()
            range_match = re.search(r"(.+?)\s*[-–—]\s*(.+)", period)
            if range_match:
                exp["startDate"] = range_match.group(1).strip()
                end = range_match.group(2).strip()
                if end.lower() not in ("present", "nay", "current", "hien tai"):
                    exp["endDate"] = end
            else:
                exp["startDate"] = period

        if from_col >= 0 and row[from_col] and not is_form_label(row[from_col]):
            exp.setdefault("startDate", row[from_col].strip())
        if to_col >= 0 and row[to_col] and not is_form_label(row[to_col]):
            exp.setdefault("endDate", row[to_col].strip())
        if company_col >= 0 and row[company_col] and not is_form_label(row[company_col]):
            exp["employer"] = row[company_col].strip()
        if position_col >= 0 and row[position_col] and not is_form_label(row[position_col]):
            exp["startTitle"] = row[position_col].strip()

        if exp.get("employer") or exp.get("startTitle"):
            result.experience.append(exp)


def _parse_education_table(table: list[list[str]], result: ExtractedFields):
    """Parse a structured education table from HR forms."""
    if result.education:
        return

    header = [strip_diacritics(c) for c in table[0]]
    school_col = degree_col = from_col = to_col = year_col = major_col = -1
    for i, h in enumerate(header):
        h_clean = re.sub(r"[^a-z0-9\s]", "", h).strip()
        if any(kw in h_clean for kw in [
            "truong", "school", "university", "institution",
        ]):
            school_col = i
        elif any(kw in h_clean for kw in ["bang cap", "degree"]):
            degree_col = i
        elif any(kw in h_clean for kw in ["field", "major", "nganh", "chuyen nganh"]):
            major_col = i
        elif h_clean in ("tu", "from"):
            from_col = i
        elif h_clean in ("toi", "to", "den"):
            to_col = i
        elif h_clean in ("year", "nam"):
            year_col = i

    for row in table[1:]:
        edu: dict[str, str] = {}
        if school_col >= 0 and len(row) > school_col and row[school_col]:
            edu["otherSchool"] = row[school_col].strip()
        if degree_col >= 0 and len(row) > degree_col and row[degree_col]:
            edu["degree"] = row[degree_col].strip()
        if major_col >= 0 and len(row) > major_col and row[major_col]:
            edu["otherMajor"] = row[major_col].strip()
        if from_col >= 0 and len(row) > from_col and row[from_col]:
            edu["startDate"] = row[from_col].strip()
        if to_col >= 0 and len(row) > to_col and row[to_col]:
            edu["endDate"] = row[to_col].strip()
        # Handle combined "Year" column (e.g., "2012-2016")
        if year_col >= 0 and len(row) > year_col and row[year_col]:
            year_val = row[year_col].strip()
            range_match = re.search(r"(\d{4})\s*[-–—]\s*(\d{4})", year_val)
            if range_match:
                edu.setdefault("startDate", range_match.group(1))
                edu.setdefault("endDate", range_match.group(2))
            else:
                edu.setdefault("startDate", year_val)
        if edu.get("otherSchool") or edu.get("degree"):
            result.education.append(edu)


def _parse_certificate_table(table: list[list[str]], result: ExtractedFields):
    """Parse a structured certificate table (e.g., Certification | Issuer | Year | ID)."""
    if result.certificates:
        return

    header = [strip_diacritics(c) for c in table[0]]
    name_col = issuer_col = year_col = -1
    for i, h in enumerate(header):
        h_clean = re.sub(r"[^a-z0-9\s/]", "", h).strip()
        if any(kw in h_clean for kw in [
            "certification", "certificate", "chung chi", "name",
        ]):
            name_col = i
        elif any(kw in h_clean for kw in ["issuer", "noi cap", "organization", "to chuc"]):
            issuer_col = i
        elif any(kw in h_clean for kw in ["year", "nam", "date", "ngay"]):
            year_col = i

    if name_col < 0:
        name_col = 0

    for row in table[1:]:
        if len(row) <= name_col:
            continue
        name_val = row[name_col].strip() if row[name_col] else ""
        if not name_val or name_val.lower() in CERT_HEADER_NAMES:
            continue
        cert: dict[str, str] = {"name": name_val}
        if issuer_col >= 0 and len(row) > issuer_col and row[issuer_col]:
            cert["institution"] = row[issuer_col].strip()
        if year_col >= 0 and len(row) > year_col and row[year_col]:
            cert["startDate"] = row[year_col].strip()
        result.certificates.append(cert)


def _parse_language_table(table: list[list[str]], result: ExtractedFields):
    """Parse a structured language table (e.g., Language | R | W | S | L | Certificate)."""
    if result.languages:
        return

    header = [strip_diacritics(c) for c in table[0]]
    lang_col = cert_col = -1
    for i, h in enumerate(header):
        h_clean = re.sub(r"[^a-z0-9\s]", "", h).strip()
        if any(kw in h_clean for kw in ["language", "ngoai ngu", "ngon ngu"]):
            lang_col = i
        elif any(kw in h_clean for kw in ["certificate", "chung chi"]):
            cert_col = i

    if lang_col < 0:
        lang_col = 0

    seen: set[str] = set()
    for row in table[1:]:
        if len(row) <= lang_col:
            continue
        lang_val = row[lang_col].strip() if row[lang_col] else ""
        if not lang_val:
            continue
        lang_lower = lang_val.lower()
        if lang_lower in LANGUAGE_NON_NAMES or lang_lower in seen:
            continue
        seen.add(lang_lower)
        entry: dict[str, str] = {"language": lang_val}
        if cert_col >= 0 and len(row) > cert_col and row[cert_col]:
            cert_val = row[cert_col].strip()
            if cert_val and cert_val.lower() not in LANGUAGE_NON_NAMES:
                entry["remark"] = cert_val
        result.languages.append(entry)


_LANG_KV_KEYS = {"languages", "language", "ngon ngu", "ngoai ngu", "foreign languages"}
_INLINE_LANG_RE = re.compile(
    r"([A-Za-zÀ-ɏ]+(?:\s[A-Za-zÀ-ɏ]+)?)"
    r"\s*(?:\(([^)]+)\)|[-–—:]\s*([A-Za-z0-9.]+))?",
)


def _parse_inline_languages(kv_pairs: dict[str, str]) -> list[dict[str, str]]:
    """Parse inline language strings like 'English (Native), Spanish (B2), Portuguese'."""
    for label, value in kv_pairs.items():
        if strip_diacritics(label.lower().strip()) in _LANG_KV_KEYS:
            langs: list[dict[str, str]] = []
            seen: set[str] = set()
            for part in re.split(r"[,;|]", value):
                part = part.strip()
                if not part:
                    continue
                m = _INLINE_LANG_RE.match(part)
                if not m:
                    continue
                lang_name = m.group(1).strip()
                lang_low = lang_name.lower()
                if lang_low in LANGUAGE_NON_NAMES or lang_low in PROGRAMMING_LANGUAGES or lang_low in seen:
                    continue
                seen.add(lang_low)
                entry: dict[str, str] = {"language": lang_name}
                level = (m.group(2) or m.group(3) or "").strip()
                if level:
                    entry["remark"] = level
                langs.append(entry)
            if langs:
                return langs
    return []


def _extract_name_from_prominent_text(doc: ExtractedDocument, result: ExtractedFields):
    """Extract name from the largest/boldest text near the top of page 1."""
    top_blocks = sorted(
        [b for b in doc.blocks if b.page == 0],
        key=lambda b: (-b.font_size, b.y0),
    )

    for b in top_blocks[:15]:
        text = b.text.strip()
        # Skip multiline blocks
        if "\n" in text:
            text = text.split("\n")[0].strip()

        if not _is_valid_name(text):
            continue

        if b.font_size >= 13 or (b.is_bold and b.font_size >= 11):
            result.personal["fullName"] = text
            parsed = parse_vietnamese_name(text)
            result.personal["firstName"] = parsed.first_name
            result.personal["lastName"] = parsed.last_name
            if parsed.middle_name:
                result.personal["middleName"] = parsed.middle_name
            result.confidence["fullName"] = 0.7
            return


_spacy_nlp = None

def _get_spacy():
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
        except Exception:
            return None
    return _spacy_nlp


def _ner_extract_name(doc: ExtractedDocument, result: ExtractedFields):
    """Use spaCy NER as last-resort fallback to find person names."""
    nlp = _get_spacy()
    if nlp is None:
        return

    head_text = doc.raw_text[:800]
    ner_doc = nlp(head_text)

    for ent in ner_doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if _is_valid_name(name) and _looks_like_vn_name(name):
                result.personal["fullName"] = name
                parsed = parse_vietnamese_name(name)
                result.personal.setdefault("firstName", parsed.first_name)
                result.personal.setdefault("lastName", parsed.last_name)
                if parsed.middle_name:
                    result.personal.setdefault("middleName", parsed.middle_name)
                result.confidence["fullName"] = 0.4
                break


def _validate_fields(result: ExtractedFields):
    """Post-extraction validation and cleanup."""
    # Validate phone: must have enough digits
    phone = result.personal.get("cellPhone", "")
    phone_digits = re.sub(r"[^\d]", "", phone)
    if phone and not (7 <= len(phone_digits) <= 15):
        del result.personal["cellPhone"]

    # Validate email: extract email if value has extra text
    email = result.personal.get("primaryEmail", "")
    if email and not REGEX_EMAIL.fullmatch(email):
        email_match = REGEX_EMAIL.search(email)
        if email_match:
            result.personal["primaryEmail"] = email_match.group(0)
        else:
            del result.personal["primaryEmail"]

    # Validate fullName: must pass name check
    full_name = result.personal.get("fullName", "")
    if full_name and not _is_valid_name(full_name):
        for key in ("fullName", "firstName", "lastName", "middleName"):
            result.personal.pop(key, None)

    # Validate idCard: must be 9 or 12 digits
    id_card = result.personal.get("idCard", "")
    if id_card:
        id_digits = re.sub(r"[^\d]", "", id_card)
        if len(id_digits) not in (9, 12):
            del result.personal["idCard"]

    # Clean contactEmail
    contact = result.personal.get("contactEmail", "")
    if contact and not REGEX_EMAIL.fullmatch(contact):
        contact_match = REGEX_EMAIL.search(contact)
        if contact_match:
            result.personal["contactEmail"] = contact_match.group(0)
        else:
            del result.personal["contactEmail"]

    # Clean address: strip pipe-separated garbage (e.g., "addr | Ngay sinh: ...")
    addr = result.personal.get("address", "")
    if addr and "|" in addr:
        result.personal["address"] = addr.split("|")[0].strip()

    # Filter noise from section results
    result.languages = [
        lang for lang in result.languages
        if lang.get("language") and not is_noise(lang["language"]) and not is_form_label(lang["language"])
        and len(lang["language"]) > 1
        and not lang["language"].replace(".", "").isdigit()
        and strip_diacritics(lang["language"].lower().strip()) not in LANGUAGE_NON_NAMES
        and lang["language"].lower().strip() not in PROGRAMMING_LANGUAGES
        and "____" not in lang.get("language", "")
        and "____" not in lang.get("remark", "")
    ]
    # Deduplicate languages by name
    seen_langs: set[str] = set()
    deduped_langs: list[dict[str, str]] = []
    for lang in result.languages:
        key = strip_diacritics(lang["language"].lower().strip())
        if key not in seen_langs:
            seen_langs.add(key)
            deduped_langs.append(lang)
    result.languages = deduped_langs

    result.awards = [
        a for a in result.awards
        if a.get("name") and not is_form_label(a["name"])
        and "TUYỂN DỤNG" not in a.get("name", "").upper()
        and "THÔNG QUA" not in a.get("name", "").upper()
        and len(a.get("name", "")) < 120
    ]

    result.certificates = [
        c for c in result.certificates
        if c.get("name") and len(c["name"]) > 2 and c["name"] != "-"
        and not is_form_label(c["name"])
        and c["name"].lower().strip() not in CERT_HEADER_NAMES
    ]

    result.experience = [
        e for e in result.experience
        if (e.get("employer") or e.get("startTitle"))
        and not is_form_label(e.get("employer", ""))
        and not is_form_label(e.get("startTitle", ""))
        and "chi tiết về" not in e.get("employer", "").lower()
        and "giải thích cho" not in e.get("employer", "").lower()
        and strip_diacritics(e.get("startTitle", "").lower().rstrip(":").strip()) not in EXP_NON_ENTRIES
        and strip_diacritics(e.get("employer", "").lower().rstrip(":").strip()) not in EXP_NON_ENTRIES
    ]

    result.education = [
        e for e in result.education
        if (e.get("otherSchool") or e.get("degree") or e.get("startDate"))
        and "mục tiêu" not in e.get("otherSchool", "").lower()
        and not is_form_label(e.get("otherSchool", ""))
    ]

    # Move education-like entries from certificates to education
    _DEGREE_PATTERNS = re.compile(
        r"\b(B\.?[AS]\.?|M\.?[AS]\.?|Ph\.?D|Bachelor|Master|Doctor|MBA|Engineer)\b",
        re.IGNORECASE,
    )
    if not result.education:
        moved = []
        kept = []
        for c in result.certificates:
            name = c.get("name", "") + " " + c.get("description", "")
            if _DEGREE_PATTERNS.search(name):
                # Parse education from certificate name like "B.A. Banking & Finance — Academy (2009-2013)"
                edu: dict[str, str] = {}
                deg_match = _DEGREE_PATTERNS.search(c.get("name", ""))
                if deg_match:
                    edu["degree"] = deg_match.group(1)
                dash_parts = re.split(r"\s*[—–-]\s*", c.get("name", ""))
                for dp in dash_parts:
                    if any(kw in dp.lower() for kw in ["university", "academy", "institute", "college", "school", "rmit", "vietnam"]):
                        edu["otherSchool"] = re.sub(r"\([\d\-–—]+\)", "", dp).strip()
                    year_range = re.search(r"\((\d{4})\s*[-–—]\s*(\d{4})\)", dp)
                    if year_range:
                        edu["startDate"] = year_range.group(1)
                        edu["endDate"] = year_range.group(2)
                if edu:
                    moved.append(edu)
            else:
                kept.append(c)
        if moved:
            result.education = moved
            result.certificates = kept


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

_EDU_GRID_HEADERS = {
    "degree": "degree", "degree/cert": "degree", "bang cap": "degree",
    "institution": "school", "school": "school", "university": "school", "truong": "school",
    "year": "year", "nam": "year",
    "gpa/grade": "grade", "gpa": "grade", "xep loai": "grade",
    "field": "field", "major": "field", "nganh": "field",
}


def _try_parse_text_grid_education(text: str) -> list[dict[str, str]] | None:
    """Detect and parse text-rendered education tables."""
    lines = [l.strip() for l in text.split("\n") if l.strip() and not is_noise(l)]
    if len(lines) < 5:
        return None

    col_types: list[str] = []
    header_end = 0
    for i, line in enumerate(lines[:8]):
        key = strip_diacritics(line.lower().rstrip(":"))
        if key in _EDU_GRID_HEADERS:
            col_types.append(_EDU_GRID_HEADERS[key])
            header_end = i + 1
        elif col_types:
            break

    # If first header was consumed by section detector, infer it
    found = set(col_types)
    if len(col_types) >= 2 and "degree" not in found and "school" in found:
        col_types.insert(0, "degree")

    if len(col_types) < 3:
        return None

    num_cols = len(col_types)
    data_lines = lines[header_end:]
    results = []
    i = 0
    while i + num_cols <= len(data_lines):
        chunk = data_lines[i:i + num_cols]
        edu: dict[str, str] = {}
        for col_idx, col_type in enumerate(col_types):
            val = chunk[col_idx]
            if not val:
                continue
            if col_type == "degree":
                edu["degree"] = val
            elif col_type == "school":
                edu["otherSchool"] = val
            elif col_type == "field":
                edu["otherMajor"] = val
            elif col_type == "year":
                range_match = re.search(r"(\d{4})\s*[-–—]\s*(\d{4})", val)
                if range_match:
                    edu["startDate"] = range_match.group(1)
                    edu["endDate"] = range_match.group(2)
                else:
                    edu["startDate"] = val
            elif col_type == "grade":
                edu["grade"] = val
        if edu.get("degree") or edu.get("otherSchool"):
            results.append(edu)
        i += num_cols

    return results if results else None


def _parse_education_section(section: Section, result: ExtractedFields | None = None) -> list[dict[str, str]]:
    grid_result = _try_parse_text_grid_education(section.text)
    if grid_result:
        # Move certification entries to certificates if they don't look like degrees
        _CERT_KEYWORDS = {"certified", "certificate", "certification", "cfa", "frm",
                          "pmp", "aws", "cisco", "itil", "professional"}
        edu_entries = []
        for entry in grid_result:
            deg = entry.get("degree", "").lower()
            if any(kw in deg for kw in _CERT_KEYWORDS) and result is not None:
                cert = {"name": entry.get("degree", "")}
                if entry.get("otherSchool"):
                    cert["institution"] = entry["otherSchool"]
                if entry.get("startDate"):
                    cert["startDate"] = entry["startDate"]
                result.certificates.append(cert)
            else:
                edu_entries.append(entry)
        return edu_entries

    _degree_re = re.compile(
        r"\b(bachelor|master|phd|ph\.d|mba|engineer|b\.s\.?|b\.a\.?|m\.s\.?|m\.a\.?"
        r"|high school|diploma|cu nhan|thac si|tien si|ky su|cao dang|thpt)\b",
        re.IGNORECASE,
    )

    # Split education entries by degree keywords (more reliable than blank lines for education)
    all_lines = [l for l in section.text.split("\n") if l.strip() and not is_noise(l.strip()) and not is_form_label(l.strip())]
    entries: list[str] = []
    current: list[str] = []
    for line in all_lines:
        stripped = line.strip()
        deg_match = _degree_re.search(stripped)
        # Only split if degree keyword appears near the start of line (within first 3 words)
        is_degree_start = False
        if deg_match:
            before = stripped[:deg_match.start()].strip()
            is_degree_start = len(before.split()) <= 2
        if current and is_degree_start and not _BULLET_RE.match(stripped) and len(stripped) < 100:
            entries.append("\n".join(current))
            current = [stripped]
        else:
            current.append(stripped)
    if current:
        entries.append("\n".join(current))
    if not entries:
        entries = _split_section_entries(section.text)

    results = []
    for entry in entries:
        edu: dict[str, str] = {}
        lines = [l.strip() for l in entry.split("\n") if l.strip() and not is_noise(l) and not is_form_label(l)]
        for line in lines:
            year_ranges = REGEX_YEAR_RANGE.findall(line)
            dates = REGEX_DATE.findall(line)

            if year_ranges:
                edu.setdefault("startDate", year_ranges[0][0])
                end = year_ranges[0][1]
                if end.lower() not in ("nay", "present", "current", "hien tai", "hiện tại"):
                    edu.setdefault("endDate", end)
            elif dates:
                if "startDate" not in edu:
                    edu["startDate"] = dates[0]
                elif "endDate" not in edu:
                    edu["endDate"] = dates[0]

            line_lower = strip_diacritics(line.lower())
            degree_keywords = {
                "bachelor": "Bachelor", "cu nhan": "Bachelor",
                "master": "Master", "thac si": "Master", "thac sy": "Master",
                "phd": "PhD", "tien si": "PhD", "tien sy": "PhD",
                "mba": "MBA",
                "engineer": "Engineer", "ky su": "Engineer",
                "college": "College", "cao dang": "College",
                "high school": "High School", "thpt": "High School",
                "certificate": "Certificate", "chung chi": "Certificate",
                "xuat sac": "Excellent",
            }
            for kw, deg in degree_keywords.items():
                if kw in line_lower:
                    edu.setdefault("degree", deg)
                    break

            if any(kw in line_lower for kw in ["university", "dai hoc", "institute", "hoc vien", "college", "truong"]):
                school_name = re.sub(r"\d{4}\s*[-–]\s*\d{4}", "", line).strip()
                school_name = re.sub(r"[|•·]", "", school_name).strip()
                if school_name and not is_form_label(school_name):
                    edu.setdefault("otherSchool", school_name)

            grade_keywords = {
                "excellent": "Excellent", "xuat sac": "Excellent",
                "very good": "Very Good", "gioi": "Good",
                "good": "Good", "kha": "Merit",
                "distinction": "Distinction",
            }
            for kw, grade in grade_keywords.items():
                if kw in line_lower:
                    edu.setdefault("grade", grade)
                    break

        if edu:
            results.append(edu)
    return results


_TEXT_GRID_HEADERS = {
    "position": "title", "title": "title", "chuc vu": "title", "vi tri": "title",
    "company": "company", "employer": "company", "ten don vi": "company",
    "from": "from", "tu": "from", "start": "from",
    "to": "to", "den": "to", "end": "to",
    "period": "period", "thoi gian": "period",
    "location": "location", "dia diem": "location",
}


def _try_parse_text_grid_experience(text: str) -> list[dict[str, str]] | None:
    """Detect and parse text-rendered tables like: Position\\nCompany\\nFrom\\nTo\\ndata..."""
    # Don't filter form labels here — "From" and "To" are valid grid headers
    lines = [l.strip() for l in text.split("\n") if l.strip() and not is_noise(l)]
    if len(lines) < 4:
        return None

    col_types: list[str] = []
    header_end = 0
    for i, line in enumerate(lines[:6]):
        key = strip_diacritics(line.lower().rstrip(":"))
        if key in _TEXT_GRID_HEADERS:
            col_types.append(_TEXT_GRID_HEADERS[key])
            header_end = i + 1
        elif col_types:
            break

    # If first header was consumed by section detector, infer it
    found = set(col_types)
    if len(col_types) >= 2 and "title" not in found and "company" in found:
        col_types.insert(0, "title")
    elif len(col_types) >= 2 and "company" not in found and "title" in found:
        col_types.insert(0, "company")

    if len(col_types) < 3:
        return None

    num_cols = len(col_types)
    data_lines = lines[header_end:]

    results = []
    i = 0
    while i + num_cols <= len(data_lines):
        chunk = data_lines[i:i + num_cols]
        if any(_BULLET_RE.match(c) for c in chunk):
            break
        exp: dict[str, str] = {}
        for col_idx, col_type in enumerate(col_types):
            val = chunk[col_idx]
            if not val:
                continue
            if col_type == "title":
                exp["startTitle"] = val
            elif col_type == "company":
                exp["employer"] = val
            elif col_type == "from":
                exp["startDate"] = val
            elif col_type == "to":
                if val.lower() not in ("present", "nay", "current"):
                    exp["endDate"] = val
            elif col_type == "period":
                range_match = re.search(r"(.+?)\s*[-–—]\s*(.+)", val)
                if range_match:
                    exp["startDate"] = range_match.group(1).strip()
                    end = range_match.group(2).strip()
                    if end.lower() not in ("present", "nay", "current"):
                        exp["endDate"] = end
        if exp.get("startTitle") or exp.get("employer"):
            results.append(exp)
        i += num_cols

    return results if results else None


def _parse_experience_section(section: Section) -> list[dict[str, str]]:
    # Detect text-rendered table grids (e.g., Position\nCompany\nFrom\nTo\ndata...)
    grid_result = _try_parse_text_grid_experience(section.text)
    if grid_result:
        return grid_result

    entries = _split_section_entries(section.text)
    results = []
    for entry in entries:
        exp: dict[str, str] = {}
        lines = [l.strip() for l in entry.split("\n") if l.strip() and not is_noise(l) and not is_form_label(l)]
        desc_lines = []

        for i, line in enumerate(lines):
            is_bullet_line = bool(_BULLET_RE.match(line))
            year_ranges = REGEX_YEAR_RANGE.findall(line)
            vn_month_ranges = REGEX_VN_MONTH_RANGE.findall(line)
            dates = REGEX_DATE.findall(line)

            if vn_month_ranges:
                m = vn_month_ranges[0]
                exp.setdefault("startDate", f"{m[0]}/{m[1]}")
                exp.setdefault("endDate", f"{m[2]}/{m[3]}")
            elif year_ranges:
                exp.setdefault("startDate", year_ranges[0][0])
                end = year_ranges[0][1]
                if end.lower() not in ("nay", "present", "current", "hien tai", "hiện tại"):
                    exp.setdefault("endDate", end)
            elif dates:
                if "startDate" not in exp:
                    exp["startDate"] = dates[0]
                elif "endDate" not in exp:
                    exp["endDate"] = dates[0]

            # Only match company/title on short non-bullet lines (headers, not descriptions)
            if not is_bullet_line and len(line) < 80:
                line_lower = line.lower()
                company_indicators = ["company", "corp", "llc", "ltd", "inc", "jsc",
                                      "công ty", "cong ty", "tnhh", "co.", "group",
                                      "bank", "ngân hàng", "telecom"]
                if any(ci in line_lower for ci in company_indicators):
                    company = re.sub(r"\d{4}\s*[-–]\s*(\d{4}|present|nay)", "", line, flags=re.IGNORECASE).strip()
                    company = re.sub(r"[|•·]", "", company).strip()
                    company = re.sub(r"T\d{1,2}/\d{4}\s*[-–]\s*T\d{1,2}/\d{4}", "", company).strip()
                    if company and not is_form_label(company):
                        exp.setdefault("employer", company)

                title_indicators = ["manager", "director", "engineer", "developer",
                                    "specialist", "analyst", "assistant", "officer",
                                    "supervisor", "lead", "head", "chief",
                                    "giám đốc", "trưởng", "chuyên viên", "nhân viên",
                                    "phó", "trợ lý", "quản lý", "senior", "intern",
                                    "thực tập", "lecturer", "researcher", "teacher",
                                    "professor", "scientist", "consultant"]
                if any(ti in line_lower for ti in title_indicators):
                    title = re.sub(r"\d{4}\s*[-–]\s*(\d{4}|present|nay)", "", line, flags=re.IGNORECASE).strip()
                    title = re.sub(r"[|•·]", "", title).strip()
                    if title and not is_form_label(title):
                        exp.setdefault("startTitle", title)

            if is_bullet_line:
                desc_lines.append(line.lstrip("-•●○*+> "))
            elif i > 1 and "employer" in exp and "startTitle" in exp:
                desc_lines.append(line)

        if desc_lines:
            exp["description"] = "; ".join(desc_lines[:10])  # cap description length

        if "employer" not in exp and lines:
            candidate = re.sub(r"\d{4}\s*[-–]\s*(\d{4}|present|nay)", "", lines[0], flags=re.IGNORECASE).strip()
            candidate = re.sub(r"[|•·]", "", candidate).strip()
            if candidate and len(candidate) > 2 and not is_form_label(candidate):
                exp["employer"] = candidate

        if exp and (exp.get("employer") or exp.get("startTitle")):
            results.append(exp)
    return results


def _parse_language_section(section: Section) -> list[dict[str, str]]:
    results = []
    lines = [l.strip() for l in section.text.split("\n")
             if l.strip() and not is_noise(l) and not is_form_label(l)]

    proficiency_map = {
        "fluent": "Fluent", "thong thao": "Fluent",
        "intermediate": "Intermediate", "trung cap": "Intermediate",
        "beginner": "Beginner", "co ban": "Beginner",
        "native": "Fluent", "advanced": "Fluent",
        "basic": "Beginner", "elementary": "Beginner",
        "good": "Intermediate", "fair": "Intermediate",
    }

    for line in lines:
        if line.replace(".", "").isdigit():
            continue
        # Skip lines with email addresses or phone numbers (reference section leak)
        if "@" in line or re.search(r"\+\d{1,3}\s*\(?\d", line):
            continue

        # Handle inline languages: "Vietnamese (Native), English (B2)" or pipe-separated
        if re.search(r"[,|]", line) and re.search(r"\([^)]+\)", line):
            inline = _parse_inline_languages({"languages": line})
            if inline:
                results.extend(inline)
                continue

        if len(line) > 80:
            continue

        lang: dict[str, str] = {}
        line_lower = strip_diacritics(line.lower())

        parts = re.split(r"[-:–|]", line, maxsplit=1)
        if len(parts) == 2:
            lang_name = parts[0].strip()
            prof_text = strip_diacritics(parts[1].strip().lower())
            if lang_name and len(lang_name) < 30:
                lang["language"] = lang_name
                for kw, level in proficiency_map.items():
                    if kw in prof_text:
                        lang["proficiency"] = level
                        break
                if "proficiency" not in lang and parts[1].strip():
                    lang["remark"] = parts[1].strip()
        elif len(line) < 30:
            lang["language"] = line.strip()

        score_match = re.search(r"(ielts|toefl|toeic)\s*[:.]?\s*([\d.]+)", line_lower)
        if score_match:
            lang["language"] = score_match.group(1).upper()
            lang["remark"] = f"Score: {score_match.group(2)}"

        if lang.get("language") and not is_form_label(lang["language"]):
            results.append(lang)
    return results


def _parse_simple_section(section: Section, name_key: str, date_key: str) -> list[dict[str, str]]:
    """Generic parser for certificates, awards, and courses sections."""
    entries = _split_section_entries(section.text)
    results = []
    for entry in entries:
        rec: dict[str, str] = {}
        lines = [l.strip() for l in entry.split("\n")
                 if l.strip() and not is_noise(l) and not is_form_label(l)]
        if lines:
            rec[name_key] = lines[0]
        for line in lines[1:]:
            dates = REGEX_DATE.findall(line)
            if dates:
                rec.setdefault(date_key, dates[0])
                if len(dates) > 1:
                    rec.setdefault("endDate" if date_key == "startDate" else "startDate", dates[1])
            elif "institution" not in rec:
                rec["institution"] = line
            elif "description" not in rec and len(line) > 20:
                rec["description"] = line
        if (rec.get(name_key) and len(rec[name_key]) > 2 and rec[name_key] != "-"
                and "TUYỂN DỤNG" not in rec.get(name_key, "").upper()):
            results.append(rec)
    return results


def _parse_certificate_section(section: Section) -> list[dict[str, str]]:
    lines = [l.strip() for l in section.text.split("\n")
             if l.strip() and not is_noise(l) and not is_form_label(l)]
    bullet_lines = [l for l in lines if _BULLET_RE.match(l)]
    numbered_lines = [l for l in lines if _NUMBERED_RE.match(l)]
    list_lines = bullet_lines if len(bullet_lines) >= len(numbered_lines) else numbered_lines

    if len(list_lines) >= 2 and len(list_lines) >= len(lines) * 0.5:
        results = []
        for line in list_lines:
            name = re.sub(r"^(\d{1,2}[.)]\s*|[-•●○*+>]\s*)", "", line).strip()
            if name and len(name) > 2:
                rec: dict[str, str] = {"name": name}
                year_match = re.search(r"\((\d{4})\)", name)
                if year_match:
                    rec["startDate"] = year_match.group(1)
                results.append(rec)
        if results:
            return results

    return _parse_simple_section(section, "name", "startDate")


def _parse_awards_section(section: Section) -> list[dict[str, str]]:
    lines = [l.strip() for l in section.text.split("\n")
             if l.strip() and not is_noise(l) and not is_form_label(l)]
    bullet_lines = [l for l in lines if _BULLET_RE.match(l)]

    if len(bullet_lines) >= 2 and len(bullet_lines) >= len(lines) * 0.6:
        results = []
        for line in bullet_lines:
            name = line.lstrip("-•●○*+> ").strip()
            if name and len(name) > 2:
                rec: dict[str, str] = {"name": name}
                year_match = re.search(r"\((\d{4})\)", name)
                if year_match:
                    rec["issueDate"] = year_match.group(1)
                results.append(rec)
        if results:
            return results

    return _parse_simple_section(section, "name", "issueDate")


def _parse_courses_section(section: Section) -> list[dict[str, str]]:
    return _parse_simple_section(section, "course", "endDate")


def _parse_family_section(section: Section) -> list[dict[str, str]]:
    entries = _split_section_entries(section.text)
    results = []
    for entry in entries:
        member: dict[str, str] = {}
        lines = [l.strip() for l in entry.split("\n")
                 if l.strip() and not is_noise(l) and not is_form_label(l)]
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                k_lower = strip_diacritics(k.strip().lower())
                v = v.strip()
                if any(x in k_lower for x in ["ten", "name", "ho ten"]):
                    member["name"] = v
                elif any(x in k_lower for x in ["quan he", "relationship"]):
                    member["relationship"] = v
                elif any(x in k_lower for x in ["dien thoai", "phone", "tel", "contact"]):
                    member["contact"] = v
                elif any(x in k_lower for x in ["chuc vu", "position", "vi tri"]):
                    member["position"] = v
        if member:
            results.append(member)
    return results


def _split_section_entries(text: str) -> list[str]:
    """Split section text into individual entries.
    Splits on blank lines, separators, and bullet-to-non-bullet transitions.
    """
    lines = text.split("\n")
    entries: list[str] = []
    current: list[str] = []
    had_bullet = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append("\n".join(current))
                current = []
                had_bullet = False
            continue

        if stripped.startswith(("---", "===", "***")):
            if current:
                entries.append("\n".join(current))
                current = []
                had_bullet = False
            continue

        is_bullet = bool(_BULLET_RE.match(stripped))

        start_new = False
        if had_bullet and not is_bullet:
            # Only split on bullet→non-bullet if the new line looks like an entry header
            # (starts uppercase, has date, pipe separator, or is short structured text)
            if (stripped[0].isupper() and (
                REGEX_YEAR_RANGE.search(stripped) or "|" in stripped
                or REGEX_DATE.search(stripped) or len(stripped) < 60
            )):
                start_new = True
        elif not is_bullet and current and REGEX_YEAR_RANGE.search(stripped):
            current_text = " ".join(current)
            if REGEX_YEAR_RANGE.search(current_text):
                start_new = True

        if start_new and current:
            entries.append("\n".join(current))
            current = [stripped]
            had_bullet = False
        else:
            current.append(stripped)
            if is_bullet:
                had_bullet = True

    if current:
        entries.append("\n".join(current))

    return entries if entries else [text]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json
    from text_extractor import extract

    if len(sys.argv) > 1:
        from cv_classifier import classify

        doc = extract(sys.argv[1])

        classification = classify(doc)
        print(f"=== CV TYPE: {classification.cv_type} (confidence: {classification.confidence}) ===")
        print(f"  Signals: {classification.signals}\n")

        fields = extract_fields(doc, cv_type=classification.cv_type)

        print("=== PERSONAL ===")
        for k, v in fields.personal.items():
            conf = fields.confidence.get(k, 1.0)
            print(f"  {k}: {v}  (confidence: {conf:.1f})")

        for section_name, entries in [
            ("EDUCATION", fields.education), ("EXPERIENCE", fields.experience),
            ("LANGUAGES", fields.languages), ("CERTIFICATES", fields.certificates),
            ("AWARDS", fields.awards), ("COURSES", fields.courses), ("FAMILY", fields.family),
        ]:
            print(f"\n=== {section_name} ({len(entries)} entries) ===")
            for e in entries:
                print(f"  {json.dumps(e, ensure_ascii=False)}")

        print(f"\n=== RAW KV PAIRS ({len(fields.raw_kv)}) ===")
        for k, v in fields.raw_kv.items():
            print(f"  {k}: {v}")
    else:
        print("Usage: python field_extractor.py <file.pdf|file.docx>")
