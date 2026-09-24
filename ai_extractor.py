"""
AI-based field extraction using a self-hosted SLM (Ollama / llama.cpp / vLLM).

Flow:  layout text -> [chunks] -> SLM -> canonical JSON -> grounding/repair
       -> schema_mapping -> ExtractedFields (SAP field ids)

The SLM only ever produces the canonical JSON defined in canonical.py, with
the exact prompt used for fine-tuning (training/). Constrained decoding with
the canonical JSON Schema is requested so small models always emit valid JSON.
"""
from __future__ import annotations

import json
import os
import re

import requests

from canonical import (
    build_messages, coerce, find_hints, ground, json_schema, merge_canonical,
    split_for_llm,
)
from schema_loader import Schema
from schema_mapping import ExtractedFields, map_canonical  # noqa: F401  (re-exported)
from text_extractor import ExtractedDocument, extract_key_value_pairs

# --- Configuration ---
# llama.cpp server:  http://localhost:8080/v1
# Ollama:            http://localhost:11434/v1
# vLLM:              http://localhost:8000/v1
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:e2b")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
# ~4k tokens of CV text per call; longer CVs are split on section headings
LLM_MAX_INPUT_CHARS = int(os.environ.get("LLM_MAX_INPUT_CHARS", "12000"))
# json_schema (constrained decoding) | json (JSON mode) | off
LLM_STRUCTURED = os.environ.get("LLM_STRUCTURED", "json_schema").lower()

_structured_unsupported: set[str] = set()


def call_llm(messages: list[dict], *, base_url: str | None = None, model: str | None = None,
             api_key: str | None = None, max_tokens: int | None = None,
             structured: str | None = None, timeout: int | None = None,
             temperature: float = 0.0) -> str:
    """Call an OpenAI-compatible chat endpoint and return the message text."""
    base_url = (base_url or LLM_BASE_URL).rstrip("/")
    model = model or LLM_MODEL
    structured = (structured or LLM_STRUCTURED).lower()
    url = f"{base_url}/chat/completions"
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or LLM_MAX_TOKENS,
        "stream": False,
        "reasoning_effort": "none",
    }
    key = f"{base_url}|{model}"
    if structured == "json_schema" and key not in _structured_unsupported:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "cv", "schema": json_schema(), "strict": True},
        }
    elif structured == "json" and key not in _structured_unsupported:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key or LLM_API_KEY}"} if (api_key or LLM_API_KEY) else {}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout or LLM_TIMEOUT)
        if resp.status_code in (400, 422) and "response_format" in payload:
            # server without structured-output support: retry unconstrained
            _structured_unsupported.add(key)
            payload.pop("response_format")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout or LLM_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to LLM server at {base_url}. "
            f"Start it with: llama-server -m <model.gguf> --port 8080  OR: ollama serve"
        )
    except requests.Timeout:
        raise TimeoutError(
            f"LLM request timed out after {timeout or LLM_TIMEOUT}s. "
            f"Try increasing LLM_TIMEOUT or lowering LLM_MAX_INPUT_CHARS."
        )
    except requests.HTTPError as e:
        raise RuntimeError(f"LLM API error: {e}: {resp.text[:300]}")


def _close_truncated_json(text: str) -> str:
    """Best-effort completion of JSON cut off by max_tokens."""
    stack, in_str, esc = [], False, False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    out = text + ('"' if in_str else "")
    out = re.sub(r",\s*$", "", out)
    out = re.sub(r',\s*"[^"]*"\s*:?\s*$', "", out)  # dangling key
    return out + "".join(reversed(stack))


def parse_llm_json(raw: str) -> dict:
    """Parse JSON from the LLM response, handling fences, prose and truncation."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object in LLM output: {raw[:300]}")
    text = text[start:]
    end = text.rfind("}")
    candidates = [text[:end + 1]] if end > 0 else []
    candidates.append(_close_truncated_json(text))
    for cand in candidates:
        for variant in (cand, re.sub(r",\s*([}\]])", r"\1", cand)):
            try:
                return json.loads(variant)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Failed to parse LLM JSON output: {raw[:300]}")


def extract_canonical(doc: ExtractedDocument, **llm_kwargs) -> tuple[dict, dict[str, float], list[str]]:
    """Run the SLM over the document and return (canonical, confidence, warnings)."""
    text = doc.layout_text or doc.raw_text
    if not text.strip():
        return {"personal": {}}, {}, ["Document has no extractable text"]

    warnings: list[str] = []
    chunks = split_for_llm(text, LLM_MAX_INPUT_CHARS)
    if len(chunks) > 1:
        warnings.append(f"Long CV split into {len(chunks)} LLM calls")
    parts = []
    for i, chunk in enumerate(chunks):
        hints = find_hints(chunk, doc.links if i == 0 else None)
        messages = build_messages(chunk, hints)
        raw = call_llm(messages, **llm_kwargs)
        try:
            parsed = parse_llm_json(raw)
        except ValueError:
            # one retry: a different sample often fixes a malformed generation
            raw = call_llm(messages, temperature=0.3, **llm_kwargs)
            try:
                parsed = parse_llm_json(raw)
            except ValueError as e:
                warnings.append(f"Chunk {i + 1}: {e}")
                continue
        parts.append(coerce(parsed))

    merged = merge_canonical(parts) if parts else {"personal": {}}
    all_hints = find_hints(text, doc.links)
    grounded, confidence = ground(merged, text, all_hints)
    dropped = [p for p, c in confidence.items() if c < 0.75]
    if dropped:
        warnings.append(f"Dropped {len(dropped)} value(s) not found in the CV text: "
                        + ", ".join(dropped[:8]))
    return grounded, confidence, warnings


def extract_fields(doc: ExtractedDocument, cv_type: str = "free_form",
                   schema: Schema | None = None, mapper=None) -> ExtractedFields:
    """Extract SAP-keyed fields from a document using the self-hosted SLM."""
    if schema is None:
        from schema_loader import load_schema
        schema = load_schema()

    canonical, confidence, warnings = extract_canonical(doc)
    result = map_canonical(canonical, schema, mapper)
    result.confidence = confidence
    result.warnings = warnings + list(doc.warnings)
    result.raw_kv = extract_key_value_pairs(doc)
    return result


if __name__ == "__main__":
    import sys
    from text_extractor import extract as extract_doc

    if len(sys.argv) < 2:
        print("Usage: python ai_extractor.py <cv file>")
        print()
        print("Prints the canonical JSON produced by the SLM (before SAP mapping).")
        print(f"  LLM_BASE_URL        = {LLM_BASE_URL}")
        print(f"  LLM_MODEL           = {LLM_MODEL}")
        print(f"  LLM_STRUCTURED      = {LLM_STRUCTURED}")
        print(f"  LLM_MAX_INPUT_CHARS = {LLM_MAX_INPUT_CHARS}")
        sys.exit(1)

    doc = extract_doc(sys.argv[1])
    canonical, confidence, warnings = extract_canonical(doc)
    print(json.dumps(canonical, indent=2, ensure_ascii=False))
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
