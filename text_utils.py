"""Shared text utilities used across the CV parser pipeline."""
import functools
import re
import unicodedata


@functools.lru_cache(maxsize=4096)
def strip_diacritics(s: str) -> str:
    """Remove diacritics and lowercase. Cached for repeated calls on static data."""
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")


@functools.lru_cache(maxsize=4096)
def normalize_label(s: str) -> str:
    """Strip diacritics, remove punctuation, collapse spaces. For label matching."""
    s = strip_diacritics(s)
    s = _PUNCT_RE.sub(" ", s)
    return _MULTI_SPACE_RE.sub(" ", s).strip()


# ---------------------------------------------------------------------------
# Raw text cleanup (applied to every line coming out of PDF/DOCX/OCR)
# ---------------------------------------------------------------------------

_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
    "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}
# Bullet-like glyphs used by CV templates -> one canonical bullet
_BULLET_CHARS = "•●○◦▪▫■□◆◇►▶▸‣⁃➢➤➔→✓✔✗☐☑❖⦿∙·"
_BULLET_LINE_RE = re.compile(rf"^\s*[{re.escape(_BULLET_CHARS)}]\s*")
_DASH_BULLET_RE = re.compile(r"^\s*[-–—*+]\s+")
# Control chars (unmapped glyphs), private-use-area icon fonts (FontAwesome), zero-width chars
_INVISIBLE_RE = re.compile("[\x00-\x08\x0b-\x1f\x7f\ue000-\uf8ff\u200b-\u200f\u2060\ufeff\u00ad\ufffd]")
_SPACES_RE = re.compile(r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")


def clean_line(s: str) -> str:
    """Normalize one line of extracted text.

    - NFC-normalizes (PDFs often store Vietnamese as base letter + combining mark)
    - expands ligatures, drops icon-font / zero-width glyphs
    - normalizes bullets to "• " and collapses whitespace
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    for lig, rep in _LIGATURES.items():
        if lig in s:
            s = s.replace(lig, rep)
    s = _INVISIBLE_RE.sub("", s)
    s = _SPACES_RE.sub(" ", s).strip()
    if _BULLET_LINE_RE.match(s):
        s = "• " + _BULLET_LINE_RE.sub("", s)
    elif _DASH_BULLET_RE.match(s):
        s = "• " + _DASH_BULLET_RE.sub("", s)
    return s


def is_bullet(s: str) -> bool:
    return s.startswith("• ")


_HYPHEN_END_RE = re.compile(r"[a-zà-ỹ]-$")


def join_wrapped(prev: str, nxt: str) -> str:
    """Join a wrapped line to the previous one, undoing end-of-line hyphenation."""
    if _HYPHEN_END_RE.search(prev) and nxt[:1].islower():
        return prev[:-1] + nxt
    return prev + " " + nxt


def normalize_for_match(s: str) -> str:
    """Aggressive normalization for grounding/overlap checks: no diacritics,
    no punctuation, single spaces, lowercase."""
    return normalize_label(s)


_DIGITS_RE = re.compile(r"\D+")


def digits_only(s: str) -> str:
    return _DIGITS_RE.sub("", s or "")
