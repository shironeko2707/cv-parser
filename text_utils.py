"""Shared text utilities used across the CV parser pipeline."""
import functools
import re
import unicodedata


@functools.lru_cache(maxsize=4096)
def strip_diacritics(s: str) -> str:
    """Remove diacritics and lowercase. Cached for repeated calls on static data."""
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
