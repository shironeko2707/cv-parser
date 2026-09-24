"""
Normalizes various date formats found in CVs to the /Date(epoch_ms)/ format
used by the target JSON schema.
"""
import re
from datetime import datetime, timezone

# Far-future date used as "no end date" / ongoing
FAR_FUTURE_EPOCH_MS = 253402214400000  # 9999-12-31


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

    # "present", "current", "nay", etc. -> far future
    ongoing_words = {"present", "current", "now", "nay", "hien tai", "hiện tại",
                     "den nay", "đến nay", "ongoing"}
    if date_str.lower() in ongoing_words:
        if default_ongoing:
            return f"/Date({FAR_FUTURE_EPOCH_MS})/"
        return None

    dt = _parse_date(date_str)
    if dt is None:
        return None

    epoch_ms = int(dt.timestamp() * 1000)
    return f"/Date({epoch_ms})/"


def _parse_date(s: str) -> datetime | None:
    """Try multiple date formats to parse the string."""
    s = s.strip()

    # Year only: "2020"
    if re.fullmatch(r"\d{4}", s):
        return datetime(int(s), 1, 1, tzinfo=timezone.utc)

    # MM/YYYY or MM-YYYY
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{4})", s)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return datetime(year, month, 1, tzinfo=timezone.utc)

    # dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%m/%d/%Y", "%m-%d-%Y",
                "%Y/%m/%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # dd/mm/yy
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + y if y < 50 else 1900 + y
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(year, mo, d, tzinfo=timezone.utc)
            except ValueError:
                pass

    # "Month dd, yyyy" or "dd Month yyyy"
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
                "%B %d %Y", "%b %d %Y", "%B, %Y", "%b %Y", "%B %Y"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    # "tháng MM năm YYYY" or "thang MM nam YYYY"
    m = re.search(r"(?:thang|tháng)\s+(\d{1,2})\s*[/,\s]*\s*(?:nam|năm)\s+(\d{4})", s, re.IGNORECASE)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return datetime(year, month, 1, tzinfo=timezone.utc)

    return None


if __name__ == "__main__":
    tests = [
        "15/03/1995",
        "2020",
        "03/2020",
        "Sep 2020",
        "September 15, 2020",
        "15 Sep 2020",
        "2020-09-15",
        "present",
        "nay",
        "hiện tại",
        "tháng 3 năm 2020",
        "thang 9, nam 2021",
        "01/01/90",
        "/Date(726537600000)/",
        "invalid",
    ]
    for t in tests:
        result = to_date_string(t, default_ongoing=True)
        print(f"  '{t}' -> {result}")
