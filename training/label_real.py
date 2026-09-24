"""
Create draft labels for REAL CVs, to be corrected by a human and used for
fine-tuning / evaluation. Real, corrected data is the most valuable training
signal -- even 100-300 verified CVs make a large difference.

    # drafts from the current model (Ollama/llama.cpp from LLM_BASE_URL / LLM_MODEL)
    python -m training.label_real ./real_cvs --out labels/

    # drafts from a bigger self-hosted teacher model (better drafts, less correction)
    python -m training.label_real ./real_cvs --out labels/ \
        --teacher-url http://gpu-box:8000/v1 --teacher-model Qwen/Qwen3-32B

    # check labels (JSON validity, values not found in the text, verified count)
    python -m training.label_real --check labels/

For every CV this writes
    labels/<name>.txt    the exact text the model sees (from text_extractor)
    labels/<name>.json   {"verified": false, "source": ..., "links": [...], "canonical": {...}}

Review workflow: open both files, fix "canonical" so it matches the CV exactly
(values copied verbatim, dates as YYYY / YYYY-MM / YYYY-MM-DD, "present" for
ongoing), then set "verified": true. Only verified labels are used by
build_dataset.py (--labels labels/).

PRIVACY: labels contain personal data. Keep them on internal machines, never
send CVs to external APIs (use a self-hosted teacher), and do not commit them
(labels/ is in .gitignore).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check(label_dir: Path) -> int:
    from canonical import find_hints, ground, order_canonical

    total = verified = bad = 0
    for jf in sorted(label_dir.glob("*.json")):
        total += 1
        try:
            label = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  {jf.name}: INVALID JSON: {e}")
            bad += 1
            continue
        verified += bool(label.get("verified"))
        tf = jf.with_suffix(".txt")
        if not tf.exists():
            print(f"  {jf.name}: missing {tf.name}")
            bad += 1
            continue
        text = tf.read_text(encoding="utf-8")
        gold = order_canonical(label.get("canonical") or {})
        _, conf = ground(gold, text, find_hints(text, label.get("links") or []))
        missing = [p for p, c in conf.items() if c < 0.75]
        if missing:
            bad += 1
            print(f"  {jf.name}: not found in text / bad format: {missing[:8]}")
    print(f"{total} labels, {verified} verified, {bad} with problems")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="CV file or folder")
    ap.add_argument("--out", default="labels")
    ap.add_argument("--teacher-url", help="OpenAI-compatible endpoint of a larger self-hosted model")
    ap.add_argument("--teacher-model")
    ap.add_argument("--teacher-key")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--check", metavar="LABEL_DIR", help="validate an existing label folder")
    args = ap.parse_args()

    if args.check:
        sys.exit(check(Path(args.check)))
    if not args.input:
        ap.error("input is required (or use --check)")

    from ai_extractor import extract_canonical
    from canonical import PROMPT_VERSION
    from text_extractor import SUPPORTED_EXTENSIONS, extract

    src = Path(args.input)
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    llm = {k: v for k, v in {"base_url": args.teacher_url, "model": args.teacher_model,
                             "api_key": args.teacher_key}.items() if v}
    if args.teacher_url:
        # a big teacher benefits from a larger output budget and longer timeout
        llm.update({"max_tokens": 8192, "timeout": 600})

    for f in files:
        stem = f.stem
        jf, tf = out / f"{stem}.json", out / f"{stem}.txt"
        if jf.exists() and not args.overwrite:
            print(f"  [skip] {f.name}")
            continue
        try:
            doc = extract(f)
            canonical, _, warnings = extract_canonical(doc, **llm)
        except Exception as e:
            print(f"  [ERR]  {f.name}: {type(e).__name__}: {e}")
            continue
        tf.write_text(doc.layout_text, encoding="utf-8")
        jf.write_text(json.dumps({
            "verified": False, "source": str(f), "prompt_version": PROMPT_VERSION,
            "links": doc.links, "warnings": warnings, "canonical": canonical,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [ok]   {f.name} -> {jf}")
    print(f"\nNow review {out}/*.json against {out}/*.txt, fix values and set \"verified\": true.")


if __name__ == "__main__":
    main()
