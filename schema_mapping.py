"""
Deterministic mapping: canonical CV JSON (SLM output) -> SuccessFactors fields.

Every canonical field lists candidate SAP field ids in priority order. At
runtime they are resolved against the schema loaded from the Excel files, so
the model/training data never depend on the Excel. When the Excel changes,
run

    python schema_mapping.py

to print the resolved mapping and every schema field that nothing maps to,
then add the new id to the candidate lists below.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from schema_loader import FieldDef, Schema
from text_utils import normalize_label


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
    sections: list = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    canonical: dict = field(default_factory=dict)  # model output after grounding
    warnings: list[str] = field(default_factory=list)


# mode "first": fill the first candidate that exists in the schema
# mode "all":   fill every candidate that exists (e.g. primary + contact email)
PERSONAL_MAP: dict[str, tuple[list[str], str]] = {
    "full_name":      (["fullName", "name"], "first"),
    "gender":         (["gender", "sex"], "first"),
    "date_of_birth":  (["dateOfBirth", "birthDate", "dob"], "first"),
    "place_of_birth": (["placeOfBirth", "birthPlace", "cityOfBirth"], "first"),
    "nationality":    (["nationality", "citizenship", "country_of_citizenship"], "first"),
    "marital_status": (["maritalStatus", "marital_status"], "first"),
    "email":          (["primaryEmail", "contactEmail"], "all"),
    "phone":          (["cellPhone", "homePhone", "phone", "mobilePhone"], "first"),
    "address":        (["address", "address1", "currentAddress"], "first"),
    "city":           (["city", "cptCityProvince", "cityProvince"], "first"),
    "country":        (["country", "countryOfResidence"], "first"),
    "id_number":      (["idCard", "nationalId", "nationalIdNumber"], "first"),
    "id_issue_date":  (["idIssueDt", "idIssueDate"], "first"),
    "id_issue_place": (["idIssuePlace"], "first"),
    "linkedin":       (["linkedinUrl", "linkedIn", "linkedin", "linkedinProfile"], "first"),
    "website":        (["website", "personalWebsite", "portfolioUrl"], "first"),
    "current_title":  (["currentTitle", "jobTitle", "title"], "first"),
}

# Fallback: match schema field *labels* when no candidate id exists
PERSONAL_LABEL_HINTS: dict[str, list[str]] = {
    "gender": ["gender", "gioi tinh"],
    "date_of_birth": ["date of birth", "ngay sinh"],
    "place_of_birth": ["place of birth", "noi sinh"],
    "nationality": ["nationality", "quoc tich"],
    "marital_status": ["marital status", "tinh trang hon nhan"],
    "phone": ["mobile", "cell phone", "so dien thoai", "dien thoai"],
    "address": ["address", "dia chi"],
    "id_number": ["id card", "cmnd", "cccd", "national id"],
    "linkedin": ["linkedin"],
}

# canonical section -> (candidate SAP sections, ExtractedFields attribute)
SECTION_MAP: dict[str, tuple[list[str], str]] = {
    "education":    (["education"], "education"),
    "experience":   (["outsideWorkExperience", "workExperience"], "experience"),
    "languages":    (["languages", "language"], "languages"),
    "certificates": (["certificates", "certifications"], "certificates"),
    "awards":       (["awards"], "awards"),
    "courses":      (["courses", "trainings"], "courses"),
    "family":       (["familyMember", "family"], "family"),
}

# canonical nested field -> (candidate nested keys, mode)
# mode "picklist_or_other": first key if its picklist matches, else second key
NESTED_MAP: dict[str, dict[str, tuple[list[str], str]]] = {
    "education": {
        "institution": (["school", "otherSchool"], "picklist_or_other"),
        "degree":      (["degree"], "first"),
        "major":       (["major", "otherMajor", "fieldOfStudy"], "picklist_or_other"),
        "start_date":  (["startDate"], "first"),
        "end_date":    (["endDate", "graduationDate"], "first"),
        "grade":       (["grade", "gpa"], "first"),
    },
    "experience": {
        "job_title":   (["startTitle", "endTitle", "title"], "first"),
        "company":     (["employer", "company"], "first"),
        "location":    (["employerAddress", "employerCity", "location"], "first"),
        "start_date":  (["startDate"], "first"),
        "end_date":    (["endDate"], "first"),
        "description": (["description", "jobDescription", "responsibilities"], "first"),
    },
    "languages": {
        "language":    (["language"], "first"),
        "proficiency": (["fluency", "speakingProf", "readingProf", "writingProf", "proficiency"], "all"),
    },
    "certificates": {
        "name":   (["name", "certificateName"], "first"),
        "issuer": (["institution", "issuer", "issuedBy", "authority"], "first"),
        "date":   (["startDate", "issueDate", "date"], "first"),
    },
    "awards": {
        "name":   (["name", "awardName"], "first"),
        "issuer": (["issuedBy", "issuer", "institution"], "first"),
        "date":   (["issueDate", "date", "startDate"], "first"),
    },
    "courses": {
        "name":       (["name", "courseName"], "first"),
        "provider":   (["institution", "provider", "organization"], "first"),
        "start_date": (["startDate"], "first"),
        "end_date":   (["endDate"], "first"),
    },
    "family": {
        "full_name":     (["fullName", "name"], "first"),  # + split into first/middle/last
        "relationship":  (["relationship", "relation", "relationType"], "first"),
        "date_of_birth": (["dateOfBirth", "birthDate"], "first"),
        "occupation":    (["occupation", "job", "jobTitle"], "first"),
        "phone":         (["phone", "cellPhone", "phoneNumber"], "first"),
    },
}

HONORIFIC_RE = re.compile(r"^(Dr|Mr|Ms|Mrs|Miss|Prof|TS|ThS|PGS|GS|Ông|Bà|Anh|Chị)\.?\s+", re.IGNORECASE)


def split_name(full_name: str) -> tuple[str, str, str, str]:
    """-> (full, first, middle, last). Positional, matching the existing
    SuccessFactors convention of this project: firstName = first word
    (Vietnamese family name), lastName = last word, middle = the rest."""
    name = HONORIFIC_RE.sub("", full_name.strip())
    name = re.sub(r"\s+", " ", name)
    if name.isupper() or name.islower():
        name = " ".join(w.capitalize() for w in name.split())
    parts = name.split()
    if not parts:
        return name, "", "", ""
    if len(parts) == 1:
        return name, parts[0], "", parts[0]
    return name, parts[0], " ".join(parts[1:-1]), parts[-1]


class SchemaResolver:
    """Resolves the candidate lists above against a concrete Schema."""

    def __init__(self, schema: Schema):
        self.schema = schema
        self.top_ids = {fd.field_id.lower(): fd for fd in schema.top_level_fields}
        self.sections = {name.lower(): name for name in schema.sections}
        self.nested: dict[str, dict[str, FieldDef]] = {
            name: {fd.nested_key.lower(): fd for fd in fds if fd.nested_key}
            for name, fds in schema.sections.items()
        }

    def top_field(self, candidates: list[str], mode: str, canonical_key: str) -> list[str]:
        found = [self.top_ids[c.lower()].field_id for c in candidates if c.lower() in self.top_ids]
        if not found:
            for hint in PERSONAL_LABEL_HINTS.get(canonical_key, []):
                for fd in self.schema.top_level_fields:
                    if hint in normalize_label(fd.label):
                        found.append(fd.field_id)
                        break
                if found:
                    break
        return found if mode == "all" else found[:1]

    def section(self, candidates: list[str]) -> str | None:
        for c in candidates:
            if c.lower() in self.sections:
                return self.sections[c.lower()]
        return None

    def nested_keys(self, section: str, candidates: list[str]) -> list[FieldDef]:
        keys = self.nested.get(section, {})
        return [keys[c.lower()] for c in candidates if c.lower() in keys]


def _fill_name(target: dict, full_name: str, keymap: dict[str, str]) -> str:
    """Write first/middle/last name parts into `target` using the real-cased
    keys in `keymap` (lowercase key -> schema key). Returns the cleaned name."""
    full, first, middle, last = split_name(full_name)
    for key, value in (("firstname", first), ("middlename", middle), ("lastname", last)):
        if value and key in keymap:
            target[keymap[key]] = value
    return full


def map_canonical(canonical: dict, schema: Schema, mapper=None) -> ExtractedFields:
    """Canonical JSON -> ExtractedFields keyed by SAP field ids / nested keys.
    Values stay raw text; json_assembler does picklist + date conversion."""
    res = SchemaResolver(schema)
    out = ExtractedFields(canonical=canonical)

    personal = canonical.get("personal") or {}
    if personal.get("full_name"):
        personal = dict(personal)
        top_keys = {k: fd.field_id for k, fd in res.top_ids.items()}
        personal["full_name"] = _fill_name(out.personal, personal["full_name"], top_keys)
    for ckey, (candidates, mode) in PERSONAL_MAP.items():
        value = personal.get(ckey)
        if not value:
            continue
        for fid in res.top_field(candidates, mode, ckey):
            out.personal.setdefault(fid, value)

    for csec, (sap_candidates, attr) in SECTION_MAP.items():
        entries = canonical.get(csec) or []
        sap_section = res.section(sap_candidates)
        if not entries or not sap_section:
            continue
        nested_keys = {k: fd.nested_key for k, fd in res.nested.get(sap_section, {}).items()}
        records = []
        for entry in entries:
            rec: dict[str, str] = {}
            for cfield, value in entry.items():
                spec = NESTED_MAP.get(csec, {}).get(cfield)
                if not spec or not value:
                    continue
                candidates, mode = spec
                if csec == "family" and cfield == "full_name":
                    value = _fill_name(rec, value, nested_keys)
                fds = res.nested_keys(sap_section, candidates)
                if not fds:
                    continue
                if mode == "picklist_or_other":
                    first = fds[0]
                    other = fds[1] if len(fds) > 1 else None
                    if first.picklist_id and mapper is not None and other is not None \
                            and not mapper.match_id(first.picklist_id, value):
                        rec.setdefault(other.nested_key, value)
                    else:
                        rec.setdefault(first.nested_key, value)
                elif mode == "all":
                    for fd in fds:
                        rec.setdefault(fd.nested_key, value)
                else:
                    rec.setdefault(fds[0].nested_key, value)
            if rec:
                records.append(rec)
        setattr(out, attr, records)
    return out


def report(schema: Schema) -> str:
    """Human-readable resolution report (run this after the Excel changes)."""
    res = SchemaResolver(schema)
    lines = ["== Personal fields =="]
    used_top: set[str] = set()
    for ckey, (candidates, mode) in PERSONAL_MAP.items():
        fids = res.top_field(candidates, mode, ckey)
        used_top.update(fids)
        lines.append(f"  {ckey:16} -> {', '.join(fids) if fids else '(not in schema)'}")
    for key in ("firstName", "middleName", "lastName"):
        if key.lower() in res.top_ids:
            used_top.add(res.top_ids[key.lower()].field_id)
    unmapped = [fd for fd in schema.top_level_fields if fd.field_id not in used_top]
    lines.append("  Schema fields with no canonical source:")
    lines += [f"    - {fd.field_id} ({fd.field_type}) {fd.label}" for fd in unmapped] or ["    (none)"]

    for csec, (sap_candidates, _) in SECTION_MAP.items():
        sap = res.section(sap_candidates)
        lines.append(f"== {csec} -> {sap or '(not in schema)'} ==")
        if not sap:
            continue
        used: set[str] = set()
        for cfield, (candidates, mode) in NESTED_MAP[csec].items():
            keys = [fd.nested_key for fd in res.nested_keys(sap, candidates)]
            if mode == "first":
                keys = keys[:1]
            used.update(keys)
            lines.append(f"  {cfield:14} -> {', '.join(keys) if keys else '(none)'}")
        if csec == "family":
            used.update(k for k in ("firstName", "middleName", "lastName") if k.lower() in res.nested[sap])
        rest = [fd.nested_key for fd in schema.sections[sap] if fd.nested_key and fd.nested_key not in used]
        if rest:
            lines.append(f"  unmapped nested keys: {', '.join(rest)}")
    lines.append("== SAP sections with no canonical source ==")
    mapped = {res.section(c) for c, _ in SECTION_MAP.values()}
    lines += [f"  - {s}" for s in schema.sections if s not in mapped] or ["  (none)"]
    return "\n".join(lines)


if __name__ == "__main__":
    from schema_loader import load_schema
    print(report(load_schema()))
