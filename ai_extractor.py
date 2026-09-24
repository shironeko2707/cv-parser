"""
AI-based field extraction using a self-hosted LLM (llama.cpp / Ollama).
Replaces the rule-based field_extractor.py with an LLM call that
extracts structured data from CV text.
"""
import json
import os
import re
import requests
from dataclasses import dataclass, field
from schema_loader import Schema
from text_extractor import ExtractedDocument, extract_key_value_pairs


# --- Configuration ---
# llama.cpp server:  http://localhost:8080/v1/chat/completions
# Ollama:            http://localhost:11434/v1/chat/completions
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:e2b")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))


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


# Build the extraction prompt from the schema
def _build_field_spec(schema: Schema) -> str:
    """Build a field specification string from the Excel schema for the prompt."""
    lines = []
    lines.append("TOP-LEVEL FIELDS (extract as flat key-value):")
    for fd in schema.top_level_fields:
        hint = ""
        if fd.field_type == "DateTime":
            hint = " (date, format: dd/mm/yyyy)"
        elif fd.picklist_id:
            hint = f" (pick closest match)"
        req = " [REQUIRED]" if fd.required else ""
        lines.append(f'  - "{fd.field_id}": {fd.label}{hint}{req}')

    lines.append("")
    lines.append("NESTED SECTIONS (extract as arrays of objects):")

    section_labels = {
        "education": "Education history",
        "outsideWorkExperience": "Work / professional experience",
        "languages": "Languages spoken",
        "certificates": "Certifications and licenses",
        "awards": "Awards and recognition",
        "courses": "Training courses",
        "familyMember": "Family members / emergency contacts",
        "Disciplinary": "Disciplinary records",
    }

    for section_name, field_defs in schema.sections.items():
        label = section_labels.get(section_name, section_name)
        keys = []
        for fd in field_defs:
            if fd.nested_key:
                hint = ""
                if fd.field_type == "DateTime":
                    hint = " (date)"
                keys.append(f'"{fd.nested_key}": {fd.label}{hint}')
        lines.append(f'  - "{section_name}": {label}')
        lines.append(f'    Fields per entry: {{{", ".join(keys)}}}')

    return "\n".join(lines)


SYSTEM_PROMPT = """\
You are a CV/resume data extraction engine. Your job is to extract structured information from CV text.

RULES:
1. Extract ONLY information explicitly present in the text. Never invent or guess.
2. For names: "firstName" = family name, "middleName" = middle name(s), "lastName" = given name. For Vietnamese names like "Nguyễn Văn An": firstName=Nguyễn, middleName=Văn, lastName=An.
3. For dates, output as dd/mm/yyyy when possible. If only year, output as 01/01/yyyy.
4. If a field is not found in the text, omit it entirely — do NOT output null or empty string.
5. For work experience: "startTitle" = job title, "employer" = company name, "description" = responsibilities/achievements as a single text block.
6. For education: "otherSchool" = institution name, "degree" = degree name, "grade" = GPA or classification.
7. Output ONLY valid JSON, no markdown, no explanation, no code fences."""


def _build_user_prompt(cv_text: str, field_spec: str) -> str:
    return f"""\
Extract all fields from this CV into JSON format.

FIELD SCHEMA:
{field_spec}

OUTPUT FORMAT (JSON object):
{{
  "personal": {{<top-level field_id: value>}},
  "education": [{{<nested keys: value>}}, ...],
  "outsideWorkExperience": [{{<nested keys: value>}}, ...],
  "languages": [{{<nested keys: value>}}, ...],
  "certificates": [{{<nested keys: value>}}, ...],
  "awards": [{{<nested keys: value>}}, ...],
  "courses": [{{<nested keys: value>}}, ...],
  "familyMember": [{{<nested keys: value>}}, ...]
}}

CV TEXT:
---
{cv_text}
---

Extract all information and output as JSON:"""


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the local LLM server via OpenAI-compatible API."""
    url = f"{LLM_BASE_URL}/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
        "reasoning_effort": "none",
    }

    try:
        resp = requests.post(url, json=payload, timeout=LLM_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to LLM server at {LLM_BASE_URL}. "
            f"Start it with: llama-server -m <model.gguf> --port 8080  "
            f"OR: ollama serve"
        )
    except requests.Timeout:
        raise TimeoutError(
            f"LLM request timed out after {LLM_TIMEOUT}s. "
            f"Try increasing LLM_TIMEOUT or using a smaller model."
        )
    except Exception as e:
        raise RuntimeError(f"LLM API error: {e}")


def _parse_llm_response(raw: str) -> dict:
    """Parse JSON from the LLM response, handling common formatting issues."""
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    # Try to find JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try fixing common issues: trailing commas
        fixed = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON output: {e}\nRaw: {raw[:500]}")


def _map_to_extracted_fields(parsed: dict, schema: Schema) -> ExtractedFields:
    """Map the parsed LLM JSON into ExtractedFields structure."""
    result = ExtractedFields()

    # Top-level personal fields
    personal = parsed.get("personal", {})
    if isinstance(personal, dict):
        valid_ids = {fd.field_id for fd in schema.top_level_fields}
        for key, value in personal.items():
            if key in valid_ids and value:
                result.personal[key] = str(value).strip()

    # Section mappings: JSON key -> (ExtractedFields attribute, valid nested keys)
    section_map = {
        "education": "education",
        "outsideWorkExperience": "experience",
        "languages": "languages",
        "certificates": "certificates",
        "awards": "awards",
        "courses": "courses",
        "familyMember": "family",
        "Disciplinary": "disciplinary",
    }

    valid_keys_per_section = {}
    for section_name, field_defs in schema.sections.items():
        valid_keys_per_section[section_name] = {
            fd.nested_key for fd in field_defs if fd.nested_key
        }

    for json_key, attr_name in section_map.items():
        entries = parsed.get(json_key, [])
        if not isinstance(entries, list):
            continue

        valid_keys = valid_keys_per_section.get(json_key, set())
        cleaned = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            record = {}
            for k, v in entry.items():
                if k in valid_keys and v:
                    record[k] = str(v).strip()
            if record:
                cleaned.append(record)

        setattr(result, attr_name, cleaned)

    return result


def extract_fields(doc: ExtractedDocument, cv_type: str = "free_form",
                   schema: Schema | None = None) -> ExtractedFields:
    """
    Extract fields from document using a self-hosted LLM.
    Falls back to returning empty fields if LLM is unavailable.
    """
    if schema is None:
        from schema_loader import load_schema
        schema = load_schema()

    # Prepare text: use layout text (preserves structure) + KV pairs
    cv_text = doc.layout_text or doc.raw_text
    if not cv_text.strip():
        return ExtractedFields()

    # Truncate if too long (most models have 8K-32K context)
    max_chars = 12000
    if len(cv_text) > max_chars:
        cv_text = cv_text[:max_chars]

    # Also include KV pairs as supplementary data
    kv_pairs = extract_key_value_pairs(doc)
    if kv_pairs:
        kv_text = "\n".join(f"{k}: {v}" for k, v in kv_pairs.items())
        cv_text += f"\n\nKEY-VALUE PAIRS FOUND:\n{kv_text}"

    # Build prompt
    field_spec = _build_field_spec(schema)
    system_prompt = SYSTEM_PROMPT
    user_prompt = _build_user_prompt(cv_text, field_spec)

    # Call LLM
    raw_response = _call_llm(system_prompt, user_prompt)

    # Parse response
    parsed = _parse_llm_response(raw_response)

    # Map to ExtractedFields
    result = _map_to_extracted_fields(parsed, schema)
    result.raw_kv = kv_pairs

    return result


if __name__ == "__main__":
    import sys
    from text_extractor import extract as extract_doc
    from schema_loader import load_schema

    if len(sys.argv) < 2:
        print("Usage: python ai_extractor.py <file.pdf|file.docx>")
        print()
        print("Environment variables:")
        print(f"  LLM_BASE_URL  = {LLM_BASE_URL}")
        print(f"  LLM_MODEL     = {LLM_MODEL}")
        print(f"  LLM_TIMEOUT   = {LLM_TIMEOUT}s")
        print()
        print("Examples:")
        print("  # Ollama (default):")
        print("  ollama pull gemma4:e2b && ollama serve")
        print("  python ai_extractor.py resume.pdf")
        print()
        print("  # llama.cpp:")
        print("  LLM_BASE_URL=http://localhost:8080/v1 LLM_MODEL=gemma4-e2b python ai_extractor.py resume.pdf")
        sys.exit(1)

    schema = load_schema()
    doc = extract_doc(sys.argv[1])
    fields = extract_fields(doc, schema=schema)

    print("=== Personal ===")
    for k, v in fields.personal.items():
        print(f"  {k}: {v}")

    for section_name in ["education", "experience", "languages", "certificates", "awards"]:
        entries = getattr(fields, section_name)
        if entries:
            print(f"\n=== {section_name} ({len(entries)} entries) ===")
            for i, e in enumerate(entries):
                print(f"  [{i}] {e}")
