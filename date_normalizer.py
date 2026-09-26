"""
Normalizes various date formats found in CVs to the /Date(epoch_ms)/ format
used by the target JSON schema.
"""
import re
from datetime import datetime, timezone

from text_utils import strip_diacritics

# Far-future date used as "no end date" / ongoing
FAR_FUTURE_EPOCH_MS = 253402214400000  # 9999-12-31

ONGOING_WORDS = {
    "present", "current", "now", "nay", "hien tai", "den nay", "ongoing", "today",
    "hien nay", "cho den nay", "aujourd hui", "heute", "actualidad", "actual", "presente",
}

MONTHS = {
    # English
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    # French / German / Spanish (diacritics stripped)
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "januar": 1, "februar": 2, "marz": 3, "juni": 6, "juli": 7, "oktober": 10, "dezember": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def to_date_string(date_str: str | None, default_ongoing: bool = False) -> str | None:
    """
    Convert a date string to /Date(epoch_ms)/ format.
    Returns None if parsing fails.
    If default_ongoing is True and the value indicates "present/current", returns far-future.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Already in /Date(...)/ format
    if date_str.startswith("/Date("):
        return date_str

    if is_ongoing(date_str):
        if default_ongoing:
            return f"/Date({FAR_FUTURE_EPOCH_MS})/"
        return None

    dt = _parse_date(date_str)
    if dt is None:
        return None

    epoch_ms = int(dt.timestamp() * 1000)
    return f"/Date({epoch_ms})/"


def is_ongoing(s: str) -> bool:
    return re.sub(r"[^a-z ]", " ", strip_diacritics(s)).strip() in ONGOING_WORDS


def _valid(y: int, mo: int | None, d: int | None) -> bool:
    if not 1900 <= y <= 2100:
        return False
    if mo is not None and not 1 <= mo <= 12:
        return False
    if d is not None:
        try:
            datetime(y, mo or 1, d)
        except ValueError:
            return False
    return True


def _year(y: str) -> int:
    v = int(y)
    if len(y) == 2:
        return 2000 + v if v < 50 else 1900 + v
    return v


def parse_date_parts(s: str) -> tuple[int, int | None, int | None] | None:
    """Parse a CV date into (year, month|None, day|None) keeping its precision.

    Handles ISO, dd/mm/yyyy (day-first, falls back to month-first when the
    day-first reading is impossible), mm/yyyy, yyyy, "Mar 2020", "15 March 2020",
    "March 15, 2020", Vietnamese "T3/2020", "tháng 3/2020", "tháng 3 năm 2020",
    "ngày 15 tháng 3 năm 2020".
    """
    if not s:
        return None
    raw = s.strip()
    t = strip_diacritics(raw).strip().rstrip(".")
    t = re.sub(r"\s+", " ", t)

    # ISO: 2020-03-15 / 2020-03 / 2020/03/15 / 2020.03
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?", t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        d = int(m.group(3)) if m.group(3) else None
        return (y, mo, d) if _valid(y, mo, d) else None

    # year only
    m = re.fullmatch(r"(?:nam\s+)?(\d{4})", t)
    if m:
        y = int(m.group(1))
        return (y, None, None) if _valid(y, None, None) else None

    # Vietnamese: ngay 15 thang 3 nam 2020 / thang 3 nam 2020 / thang 3/2020 / T3/2020 / T3-2020
    m = re.fullmatch(r"(?:ngay\s+(\d{1,2})\s*,?\s*)?(?:thang|th|t)\s*\.?\s*(\d{1,2})\s*(?:[/,.\-]|\s)\s*(?:nam\s+)?(\d{4})", t)
    if m:
        d = int(m.group(1)) if m.group(1) else None
        mo, y = int(m.group(2)), int(m.group(3))
        return (y, mo, d) if _valid(y, mo, d) else None

    # dd/mm/yyyy or dd/mm/yy (day first; month first if day-first impossible)
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})", t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), _year(m.group(3))
        if _valid(y, b, a):
            return (y, b, a)
        if _valid(y, a, b):
            return (y, a, b)
        return None

    # mm/yyyy, mm-yyyy, mm.yyyy
    m = re.fullmatch(r"(\d{1,2})\s*[/\-.]\s*(\d{4})", t)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        return (y, mo, None) if _valid(y, mo, None) else None

    # textual months: "mar 2020", "march, 2020", "15 mar 2020", "march 15, 2020", "mar-20"
    words = re.findall(r"[a-z]+|\d+", t)
    month = next((MONTHS[w] for w in words if w in MONTHS), None)
    nums = [w for w in words if w.isdigit()]
    if month and nums:
        years = [n for n in nums if len(n) == 4]
        if years:
            y = int(years[0])
            rest = [int(n) for n in nums if n != years[0] and len(n) <= 2]
        elif len(nums) == 1 and len(nums[0]) == 2:
            y, rest = _year(nums[0]), []
        else:
            return None
        d = rest[0] if rest else None
        return (y, month, d) if _valid(y, month, d) else (y, month, None) if _valid(y, month, None) else None
    return None


def _parse_date(s: str) -> datetime | None:
    parts = parse_date_parts(s)
    if parts is None:
        return None
    y, mo, d = parts
    return datetime(y, mo or 1, d or 1, tzinfo=timezone.utc)


def to_iso(s: str) -> str | None:
    """CV date -> "YYYY", "YYYY-MM" or "YYYY-MM-DD" ("present" for ongoing)."""
    if is_ongoing(s):
        return "present"
    parts = parse_date_parts(s)
    if parts is None:
        return None
    y, mo, d = parts
    return f"{y:04d}" + (f"-{mo:02d}" if mo else "") + (f"-{d:02d}" if mo and d else "")


if __name__ == "__main__":
    tests = [
        "15/03/1995", "2020", "03/2020", "Sep 2020", "September 15, 2020", "15 Sep 2020",
        "2020-09-15", "2020-09", "present", "nay", "hiện tại", "Đến nay", "tháng 3 năm 2020",
        "thang 9, nam 2021", "T3/2020", "Tháng 12/2019", "ngày 5 tháng 7 năm 1998",
        "01/01/90", "12/25/2020", "/Date(726537600000)/", "invalid",
    ]
    for t in tests:
        print(f"  {t!r:28} -> {to_iso(t)!s:12} {to_date_string(t, default_ongoing=True)}")
