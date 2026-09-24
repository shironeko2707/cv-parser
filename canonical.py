"""
Canonical CV JSON: the fixed output contract of the SLM.

The model never sees SAP field ids. It emits this small, stable structure,
which is what the fine-tuning data is written in; schema_mapping.py then maps
it deterministically onto the SuccessFactors schema loaded from Excel. This
keeps training data independent of the (private, changing) Excel schema.

This module also owns everything that must be *identical* at training and
inference time: the prompt, the hint extraction, the chunking of long CVs,
and the grounding/repair of model output.
"""
from __future__ import annotations

import json
import re

from rapidfuzz import fuzz

from sections import match_section
from text_utils import digits_only, normalize_for_match

# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

PERSONAL_FIELDS = [
    "full_name", "gender", "date_of_birth", "place_of_birth", "nationality",
    "marital_status", "email", "phone", "address", "city", "country",
    "id_number", "id_issue_date", "id_issue_place", "linkedin", "website",
    "current_title",
]

SECTION_FIELDS: dict[str, list[str]] = {
    "education": ["institution", "degree", "major", "start_date", "end_date", "grade"],
    "experience": ["job_title", "company", "location", "start_date", "end_date", "description"],
    "languages": ["language", "proficiency"],
    "certificates": ["name", "issuer", "date"],
    "awards": ["name", "issuer", "date"],
    "courses": ["name", "provider", "start_date", "end_date"],
    "family": ["full_name", "relationship", "date_of_birth", "occupation", "phone"],
}

# Fields whose value is normalized (not copied verbatim from the CV)
DATE_FIELDS = {"date_of_birth", "id_issue_date", "start_date", "end_date", "date"}
ENUM_FIELDS = {"gender": ["male", "female", "other"]}

# The field that identifies an entry (used for dedup / chunk merge / eval pairing)
ENTRY_KEY_FIELDS: dict[str, list[str]] = {
    "education": ["institution", "degree"],
    "experience": ["company", "job_title"],
    "languages": ["language"],
    "certificates": ["name"],
    "awards": ["name"],
    "courses": ["name"],
    "family": ["full_name"],
}

ISO_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$")


def json_schema() -> dict:
    """JSON Schema for constrained decoding (Ollama `format`, llama.cpp grammar,
    vLLM guided_json). All fields optional; unknown keys rejected."""
    def obj(fields):
        props = {}
        for f in fields:
            if f in ENUM_FIELDS:
                props[f] = {"type": "string", "enum": ENUM_FIELDS[f]}
            else:
                props[f] = {"type": "string"}
        return {"type": "object", "properties": props, "additionalProperties": False}

    props = {"personal": obj(PERSONAL_FIELDS)}
    for sec, fields in SECTION_FIELDS.items():
        props[sec] = {"type": "array", "items": obj(fields)}
    return {"type": "object", "properties": props, "additionalProperties": False}


# ---------------------------------------------------------------------------
# Prompt (shared by inference and training — do not change one without the other)
# ---------------------------------------------------------------------------

PROMPT_VERSION = "cv-canonical-v1"

SYSTEM_PROMPT = """\
You are a CV parser. Read the CV text and output ONE JSON object with the candidate's data.

Rules:
1. Copy values exactly as written in the CV (same language, spelling, accents). Never translate, summarize or invent.
2. Leave out any field or section that is not in the CV. No nulls, no empty strings.
3. Dates: "YYYY-MM-DD", "YYYY-MM" or "YYYY", with only the precision written in the CV. Numeric dates are day-first (dd/mm/yyyy) unless impossible. "T3/2020" or "Tháng 3/2020" = "2020-03". Ongoing end date = "present".
4. gender: "male" or "female" (Nam = male, Nữ = female).
5. One entry per school, job, language, certificate, award, course and family member, in document order. A job with several positions at one company = one entry per position.
6. experience.description: that job's responsibilities/achievements, one line per bullet, joined with "\\n".
7. Skills, projects, hobbies and references are not certificates, awards or courses — leave them out.
8. current_title: the candidate's own headline/job title near their name, if written.

JSON keys:
{"personal": {"full_name", "gender", "date_of_birth", "place_of_birth", "nationality", "marital_status", "email", "phone", "address", "city", "country", "id_number", "id_issue_date", "id_issue_place", "linkedin", "website", "current_title"},
 "education": [{"institution", "degree", "major", "start_date", "end_date", "grade"}],
 "experience": [{"job_title", "company", "location", "start_date", "end_date", "description"}],
 "languages": [{"language", "proficiency"}],
 "certificates": [{"name", "issuer", "date"}],
 "awards": [{"name", "issuer", "date"}],
 "courses": [{"name", "provider", "start_date", "end_date"}],
 "family": [{"full_name", "relationship", "date_of_birth", "occupation", "phone"}]}"""


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?<![\w/.])(?:\+|00)?\(?\d{1,4}\)?[\s.\-]?(?:\(?\d{1,4}\)?[\s.\-]?){2,5}\d{2,4}(?![\w/])"
)
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s|,;]+|(?:linkedin\.com|github\.com|gitlab\.com|behance\.net)/[^\s|,;]+",
    re.IGNORECASE,
)
_YEAR_RANGE_RE = re.compile(r"^\s*(19|20)\d{2}\s*[-–—]\s*((19|20)\d{2})\s*$")


def find_phones(text: str) -> list[str]:
    out = []
    for m in PHONE_RE.finditer(text):
        s = m.group(0).strip()
        digits = digits_only(s)
        if not 9 <= len(digits) <= 15 or _YEAR_RANGE_RE.match(s):
            continue
        if re.fullmatch(r"(19|20)\d{2}\s*[-–—/.]\s*(19|20)\d{2}", s):
            continue
        if s not in out:
            out.append(s)
    return out


def find_hints(text: str, links: list[str] | None = None) -> dict[str, list[str]]:
    """Deterministic detections passed to the model and used for repair."""
    emails = []
    for e in EMAIL_RE.findall(text) + [l for l in (links or []) if EMAIL_RE.fullmatch(l)]:
        if e.lower() not in (x.lower() for x in emails):
            emails.append(e)
    urls = []
    for u in URL_RE.findall(text) + [l for l in (links or []) if not EMAIL_RE.fullmatch(l)]:
        u = u.rstrip(").")
        if "@" not in u and u.lower() not in (x.lower() for x in urls) and not u.lower().startswith("tel:"):
            urls.append(u)
    return {"emails": emails[:5], "phones": find_phones(text)[:5], "links": urls[:8]}


def build_user_prompt(cv_text: str, hints: dict[str, list[str]] | None = None) -> str:
    parts = ["CV TEXT:", "<<<", cv_text.strip(), ">>>"]
    hints = hints or {}
    lines = []
    if hints.get("emails"):
        lines.append("emails: " + " ; ".join(hints["emails"]))
    if hints.get("phones"):
        lines.append("phones: " + " ; ".join(hints["phones"]))
    if hints.get("links"):
        lines.append("links: " + " ; ".join(hints["links"]))
    if lines:
        parts += ["", "DETECTED (regex, may be incomplete):", *lines]
    parts += ["", "Output the JSON object."]
    return "\n".join(parts)


def build_messages(cv_text: str, hints: dict | None = None) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(cv_text, hints)},
    ]


def to_json_line(canonical: dict) -> str:
    """Serialization used for training targets (compact, fixed key order)."""
    return json.dumps(order_canonical(canonical), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Chunking for CVs longer than the model context
# ---------------------------------------------------------------------------

def split_for_llm(layout_text: str, max_chars: int) -> list[str]:
    """Split a long CV on section headings. Chunk 0 always holds the preamble
    (name/contact). Oversized sections are split on blank lines, repeating
    the heading so the model knows which section it is reading."""
    if len(layout_text) <= max_chars:
        return [layout_text]
    blocks: list[list[str]] = [[]]
    for line in layout_text.split("\n"):
        if line.startswith("## ") and blocks[-1]:
            blocks.append([])
        blocks[-1].append(line)

    pieces: list[str] = []
    for block in blocks:
        text = "\n".join(block).strip()
        if len(text) <= max_chars:
            pieces.append(text)
            continue
        heading = block[0] if block[0].startswith("## ") else ""
        cur = heading
        for para in text[len(heading):].split("\n\n"):
            para = para.strip()
            while len(para) > max_chars - len(heading) - 2:  # one giant paragraph
                cut = para.rfind("\n", 0, max_chars - len(heading) - 2)
                cut = cut if cut > 0 else max_chars - len(heading) - 2
                pieces.append(f"{heading}\n{para[:cut]}".strip())
                para = para[cut:].strip()
            if len(cur) + len(para) + 2 > max_chars and cur.strip() != heading:
                pieces.append(cur.strip())
                cur = heading
            cur = f"{cur}\n\n{para}" if cur else para
        if cur.strip() and cur.strip() != heading:
            pieces.append(cur.strip())

    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + len(piece) + 2 <= max_chars:
            chunks[-1] += "\n\n" + piece
        else:
            chunks.append(piece)
    return chunks


def _entry_key(section: str, entry: dict) -> tuple:
    return tuple(normalize_for_match(str(entry.get(f, ""))) for f in ENTRY_KEY_FIELDS[section])


def merge_canonical(parts: list[dict]) -> dict:
    """Merge per-chunk outputs: first value wins for personal fields,
    section entries are concatenated and de-duplicated."""
    merged: dict = {"personal": {}}
    for part in parts:
        for k, v in (part.get("personal") or {}).items():
            if v and k not in merged["personal"]:
                merged["personal"][k] = v
        for sec in SECTION_FIELDS:
            for entry in part.get(sec) or []:
                merged.setdefault(sec, []).append(entry)
    return dedupe_entries(merged)


def dedupe_entries(data: dict) -> dict:
    for sec in SECTION_FIELDS:
        entries = data.get(sec)
        if not entries:
            continue
        out, index = [], {}
        for e in entries:
            key = _entry_key(sec, e)
            if any(key) and key in index:
                # keep the richer version
                prev = out[index[key]]
                for f, v in e.items():
                    if v and (f not in prev or len(str(v)) > len(str(prev[f]))):
                        prev[f] = v
                continue
            index[key] = len(out)
            out.append(dict(e))
        data[sec] = out
    return data


def order_canonical(data: dict) -> dict:
    """Return a copy with contract key order and empty values removed."""
    out: dict = {}
    personal = {k: data["personal"][k] for k in PERSONAL_FIELDS
                if (data.get("personal") or {}).get(k)}
    if personal:
        out["personal"] = personal
    for sec, fields in SECTION_FIELDS.items():
        entries = []
        for e in data.get(sec) or []:
            if isinstance(e, dict):
                ordered = {f: e[f] for f in fields if e.get(f)}
                if ordered:
                    entries.append(ordered)
        if entries:
            out[sec] = entries
    return out


# ---------------------------------------------------------------------------
# Validation, grounding and repair of model output
# ---------------------------------------------------------------------------

def coerce(parsed) -> dict:
    """Coerce arbitrary model JSON into the contract (drop unknown keys,
    stringify scalars, accept a few common key aliases)."""
    if not isinstance(parsed, dict):
        return {"personal": {}}
    aliases = {"work_experience": "experience", "outsideWorkExperience": "experience",
               "familyMember": "family", "certifications": "certificates",
               "personal_info": "personal"}
    for a, target in aliases.items():
        if a in parsed and target not in parsed:
            parsed[target] = parsed.pop(a)
    out: dict = {"personal": {}}
    personal = parsed.get("personal")
    if isinstance(personal, dict):
        for k in PERSONAL_FIELDS:
            v = personal.get(k)
            if isinstance(v, (str, int, float)) and str(v).strip():
                out["personal"][k] = str(v).strip()
    for sec, fields in SECTION_FIELDS.items():
        entries = parsed.get(sec)
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            continue
        clean = []
        for e in entries:
            if not isinstance(e, dict):
                continue
            rec = {}
            for f in fields:
                v = e.get(f)
                if isinstance(v, list):
                    v = "\n".join(str(x) for x in v if x)
                if isinstance(v, (str, int, float)) and str(v).strip():
                    rec[f] = str(v).strip()
            if rec:
                clean.append(rec)
        if clean:
            out[sec] = clean
    return out


def _grounding_score(value: str, source_norm: str, source_tokens: set[str]) -> float:
    v = normalize_for_match(value)
    if not v:
        return 0.0
    if v in source_norm:
        return 1.0
    tokens = v.split()
    if len(tokens) > 6:  # long text (descriptions): token recall
        return sum(1 for t in tokens if t in source_tokens) / len(tokens)
    if len(v) < 4:
        return 0.0
    return fuzz.partial_ratio(v, source_norm) / 100.0


def _date_grounded(value: str, source_text: str) -> bool:
    if value.lower() == "present":
        return True
    m = ISO_DATE_RE.match(value)
    if not m:
        return False
    year = m.group(1)
    return year in source_text or year[2:] in re.findall(r"\b\d{2}\b", source_text)


def normalize_date_value(value: str) -> str | None:
    """Accept model dates that are not strict ISO (e.g. "03/2020") by
    re-normalizing them; returns ISO / "present" / None."""
    v = value.strip()
    if v.lower() in ("present", "now", "current", "nay", "hiện tại", "đến nay", "ongoing"):
        return "present"
    m = ISO_DATE_RE.match(v)
    if m:
        y, mo, d = m.groups()
        if mo and not 1 <= int(mo) <= 12:
            return y
        if d and not 1 <= int(d) <= 31:
            return f"{y}-{mo}"
        return v
    from date_normalizer import parse_date_parts
    parts = parse_date_parts(v)
    if parts is None:
        return None
    y, mo, d = parts
    return f"{y:04d}" + (f"-{mo:02d}" if mo else "") + (f"-{d:02d}" if mo and d else "")


def ground(data: dict, source_text: str, hints: dict | None = None,
           min_score: float = 0.75) -> tuple[dict, dict[str, float]]:
    """Drop values that do not occur in the source text (hallucinations),
    validate formats, and repair email/phone from regex hints.
    Returns (clean_data, confidence per field path)."""
    hints = hints or find_hints(source_text)
    source_norm = normalize_for_match(source_text + " " + " ".join(hints.get("links", [])))
    source_tokens = set(source_norm.split())
    conf: dict[str, float] = {}

    def check(path: str, field_name: str, value: str) -> str | None:
        if field_name in DATE_FIELDS:
            norm = normalize_date_value(value)
            ok = norm is not None and _date_grounded(norm, source_text)
            conf[path] = 1.0 if ok else 0.0
            return norm if ok else None
        if field_name in ENUM_FIELDS:
            v = value.lower()
            v = {"nam": "male", "nữ": "female", "nu": "female", "m": "male", "f": "female"}.get(v, v)
            ok = v in ENUM_FIELDS[field_name]
            conf[path] = 1.0 if ok else 0.0
            return v if ok else None
        if field_name == "email":
            m = EMAIL_RE.search(value)
            ok = False
            if m:
                email = m.group(0).lower()
                ok = email in source_text.lower() or \
                    any(email == h.lower() for h in hints.get("emails", []))
            conf[path] = 1.0 if ok else 0.0
            return m.group(0) if ok else None
        if field_name == "phone":
            d = digits_only(value)
            ok = len(d) >= 8 and d in digits_only(source_text)
            conf[path] = 1.0 if ok else 0.0
            return value if ok else None
        score = _grounding_score(value, source_norm, source_tokens)
        conf[path] = round(score, 2)
        return value if score >= min_score else None

    out: dict = {"personal": {}}
    for k, v in (data.get("personal") or {}).items():
        kept = check(f"personal.{k}", k, v)
        if kept:
            out["personal"][k] = kept

    # repair from deterministic detections
    if "email" not in out["personal"] and hints.get("emails"):
        out["personal"]["email"] = hints["emails"][0]
        conf["personal.email"] = 0.9
    if "phone" not in out["personal"] and hints.get("phones"):
        out["personal"]["phone"] = hints["phones"][0]
        conf["personal.phone"] = 0.8
    if "linkedin" not in out["personal"]:
        for link in hints.get("links", []):
            if "linkedin.com" in link.lower():
                out["personal"]["linkedin"] = link
                conf["personal.linkedin"] = 0.9
                break

    for sec in SECTION_FIELDS:
        entries = []
        for i, e in enumerate(data.get(sec) or []):
            rec = {}
            for f, v in e.items():
                kept = check(f"{sec}[{i}].{f}", f, v)
                if kept:
                    rec[f] = kept
            # an entry needs at least one identifying field to be kept
            if any(rec.get(f) for f in ENTRY_KEY_FIELDS[sec]):
                entries.append(rec)
        if entries:
            out[sec] = entries
    return dedupe_entries(out), conf


def restrict_to_text(data: dict, text: str, hints: dict | None = None) -> dict:
    """Keep only values grounded in `text` (used to build per-chunk training
    targets from a full-document gold label)."""
    clean, _ = ground(data, text, hints=hints or find_hints(text), min_score=0.9)
    # repair step may add hint values that the gold doesn't have: undo that
    gold_personal = data.get("personal") or {}
    clean["personal"] = {k: v for k, v in clean["personal"].items() if k in gold_personal}
    return order_canonical(clean)


def section_of_heading(line: str) -> str | None:
    return match_section(line[3:]) if line.startswith("## ") else None
