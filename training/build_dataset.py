"""
Build the SFT dataset for the CV-parsing SLM.

Every sample goes through the *production* path:
    synthetic profile -> rendered file (PDF/DOCX/...) -> text_extractor.extract()
    -> canonical.build_messages()   (identical prompt to inference)
    -> target = gold canonical JSON restricted to what the extracted text contains

Real CVs you have labeled (training/label_real.py, then human-verified) are
mixed in and up-weighted; they matter more than synthetic data.

Usage:
    python -m training.build_dataset --n 4000 --out data/
    python -m training.build_dataset --n 4000 --out data/ --labels labels/ --real-weight 3

Outputs (in --out):
    train.jsonl, val.jsonl        synthetic (+ real) samples
    val_real.jsonl                held-out real samples (if --labels), for honest eval
    stats.json                    template mix, lengths, extraction-loss per field
    docs/                         rendered files (with --keep-docs) for inspection/eval
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from canonical import (  # noqa: E402
    PROMPT_VERSION, build_messages, find_hints, ground, order_canonical, restrict_to_text,
    split_for_llm, to_json_line,
)

DEFAULT_MAX_CHARS = 12000  # keep in sync with ai_extractor.LLM_MAX_INPUT_CHARS

_gen = None
_cfg: dict = {}


def _init_worker(cfg: dict):
    global _gen, _cfg
    import warnings
    warnings.filterwarnings("ignore")
    from training.synth import ProfileGenerator
    _gen = ProfileGenerator(seed=cfg["seed"])
    _cfg = cfg


def _record(text: str, links: list[str] | None, target: dict, meta: dict, fmt: str) -> dict:
    messages = build_messages(text, find_hints(text, links))
    answer = {"role": "assistant", "content": to_json_line(target)}
    if fmt == "messages":
        return {"messages": messages + [answer], "meta": meta}
    return {"prompt": messages, "completion": [answer], "meta": meta}


def _field_count(data: dict) -> Counter:
    c: Counter = Counter()
    for k in (data.get("personal") or {}):
        c[f"personal.{k}"] += 1
    for sec, entries in data.items():
        if sec == "personal":
            continue
        for e in entries:
            for f in e:
                c[f"{sec}.{f}"] += 1
    return c


def make_synthetic(i: int) -> list[dict] | dict:
    """Render + extract one synthetic CV. Returns records (or an error dict)."""
    from text_extractor import extract
    from training.render import render

    cfg = _cfg
    seed = cfg["seed"] * 1_000_003 + i
    _gen.reseed(seed)
    rng = random.Random(seed)
    try:
        profile = _gen.generate()
        out_dir = cfg["docs_dir"] or tempfile.mkdtemp(prefix="cvsynth_")
        from training.render import pick_template
        template = pick_template(profile, rng, cfg["templates"])
        path, template = render(profile, out_dir, f"syn{i:06d}", rng, template=template)
        doc = extract(path)
        if not cfg["docs_dir"]:
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception as e:  # a broken sample must not kill the build
        return {"error": f"{type(e).__name__}: {e}", "i": i}

    text = doc.layout_text
    gold = order_canonical(profile.gold())
    target = restrict_to_text(gold, text, find_hints(text, doc.links))
    gold_c, kept_c = _field_count(gold), _field_count(target)
    meta = {"id": f"syn{i:06d}", "source": "synthetic", "template": template,
            "lang": profile.lang, "chars": len(text), "prompt_version": PROMPT_VERSION}
    if cfg["docs_dir"]:
        meta["file"] = path
        Path(path).with_suffix(".gold.json").write_text(
            json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")

    records = []
    chunks = split_for_llm(text, cfg["max_chars"])
    if len(chunks) == 1 and rng.random() < cfg["chunk_prob"] and len(text) > cfg["chunk_chars"] * 1.3:
        chunks = split_for_llm(text, cfg["chunk_chars"])  # teach partial-CV inputs too
    if len(chunks) == 1:
        records.append(_record(text, doc.links, target, meta, cfg["format"]))
    else:
        for ci, chunk in enumerate(chunks):
            links = doc.links if ci == 0 else None
            part = restrict_to_text(gold, chunk, find_hints(chunk, links))
            records.append(_record(chunk, links, part, {**meta, "id": f"{meta['id']}_c{ci}", "chunk": ci},
                                   cfg["format"]))
    return {"records": records, "gold": gold_c, "kept": kept_c, "template": template}


def load_real_labels(dirs: list[str], max_chars: int, fmt: str) -> tuple[list[dict], list[str]]:
    """Verified real labels: <stem>.txt (extracted text) + <stem>.json
    ({"verified": true, "links": [...], "canonical": {...}})."""
    records, problems = [], []
    for d in dirs:
        for jf in sorted(Path(d).glob("*.json")):
            try:
                label = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                problems.append(f"{jf.name}: invalid JSON ({e})")
                continue
            if not label.get("verified"):
                continue
            tf = jf.with_suffix(".txt")
            if not tf.exists():
                problems.append(f"{jf.name}: missing {tf.name}")
                continue
            text = tf.read_text(encoding="utf-8")
            links = label.get("links") or []
            gold = order_canonical(label.get("canonical") or {})
            _, conf = ground(gold, text, find_hints(text, links))
            missing = [p for p, c in conf.items() if c < 0.75]
            if missing:
                problems.append(f"{jf.name}: values not found in text (check the label): {missing[:6]}")
            meta = {"id": jf.stem, "source": "real", "chars": len(text), "prompt_version": PROMPT_VERSION}
            chunks = split_for_llm(text, max_chars)
            for ci, chunk in enumerate(chunks):
                ch_links = links if ci == 0 else None
                target = gold if len(chunks) == 1 else restrict_to_text(gold, chunk, find_hints(chunk, ch_links))
                m = {**meta, "chunk": ci} if len(chunks) > 1 else meta
                records.append(_record(chunk, ch_links, target, m, fmt))
    return records, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=3000, help="number of synthetic CVs")
    ap.add_argument("--out", default="data", help="output directory")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--val-frac", type=float, default=0.05)
    ap.add_argument("--labels", action="append", default=[], help="dir with verified real labels (repeatable)")
    ap.add_argument("--real-weight", type=int, default=3, help="repeat each real training sample N times")
    ap.add_argument("--real-val-frac", type=float, default=0.2, help="share of real CVs held out for eval")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="same as LLM_MAX_INPUT_CHARS")
    ap.add_argument("--chunk-prob", type=float, default=0.1, help="share of docs also trained as chunks")
    ap.add_argument("--chunk-chars", type=int, default=2500)
    ap.add_argument("--templates", nargs="*", default=None, help="restrict to these templates")
    ap.add_argument("--format", choices=["prompt_completion", "messages"], default="prompt_completion",
                    help="prompt_completion (TRL, loss on answer only) or messages (Unsloth/axolotl/LLaMA-Factory)")
    ap.add_argument("--keep-docs", action="store_true", help="keep rendered files + gold in OUT/docs/")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    docs_dir = out / "docs" if args.keep_docs else None
    if docs_dir:
        docs_dir.mkdir(exist_ok=True)
    cfg = {"seed": args.seed, "docs_dir": str(docs_dir) if docs_dir else None, "max_chars": args.max_chars,
           "chunk_prob": args.chunk_prob, "chunk_chars": args.chunk_chars, "templates": args.templates,
           "format": args.format}

    t0 = time.time()
    synthetic: list[list[dict]] = []
    gold_c, kept_c, templates, errors = Counter(), Counter(), Counter(), []
    with Pool(args.workers, initializer=_init_worker, initargs=(cfg,)) as pool:
        for n_done, res in enumerate(pool.imap_unordered(make_synthetic, range(args.n), chunksize=8), 1):
            if "error" in res:
                errors.append(res)
                continue
            synthetic.append(res["records"])
            gold_c.update(res["gold"])
            kept_c.update(res["kept"])
            templates[res["template"]] += 1
            if n_done % 200 == 0:
                print(f"  {n_done}/{args.n} docs  ({time.time() - t0:.0f}s)", flush=True)

    rng = random.Random(args.seed)
    synthetic.sort(key=lambda recs: recs[0]["meta"]["id"])
    rng.shuffle(synthetic)
    n_val = max(1, int(len(synthetic) * args.val_frac))
    val = [r for recs in synthetic[:n_val] for r in recs]
    train = [r for recs in synthetic[n_val:] for r in recs]

    real_problems: list[str] = []
    val_real: list[dict] = []
    if args.labels:
        real, real_problems = load_real_labels(args.labels, args.max_chars, args.format)
        by_doc: dict[str, list[dict]] = {}
        for r in real:
            by_doc.setdefault(r["meta"]["id"], []).append(r)
        ids = sorted(by_doc)
        rng.shuffle(ids)
        n_rv = int(len(ids) * args.real_val_frac)
        val_real = [r for i in ids[:n_rv] for r in by_doc[i]]
        train += [r for i in ids[n_rv:] for r in by_doc[i]] * args.real_weight
        print(f"Real labels: {len(ids)} verified CVs ({len(ids) - n_rv} train x{args.real_weight}, {n_rv} held out)")
    rng.shuffle(train)

    def dump(name, rows):
        with open(out / name, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("train.jsonl", train)
    dump("val.jsonl", val)
    if val_real:
        dump("val_real.jsonl", val_real)

    loss = {k: round(1 - kept_c[k] / gold_c[k], 3) for k in sorted(gold_c) if gold_c[k]}
    lengths = sorted(r["meta"]["chars"] for recs in synthetic for r in recs[:1])
    stats = {
        "prompt_version": PROMPT_VERSION, "synthetic_docs": len(synthetic), "errors": len(errors),
        "train_samples": len(train), "val_samples": len(val), "val_real_samples": len(val_real),
        "templates": dict(templates),
        "chars": {"p50": lengths[len(lengths) // 2] if lengths else 0, "max": lengths[-1] if lengths else 0},
        "extraction_loss_per_field": loss,
        "overall_extraction_loss": round(1 - sum(kept_c.values()) / max(sum(gold_c.values()), 1), 4),
        "real_label_problems": real_problems,
        "error_examples": errors[:10],
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Done in {time.time() - t0:.0f}s: {len(train)} train / {len(val)} val samples -> {out}/")
    print(f"Templates: {dict(templates)}")
    print(f"Gold values lost in extraction: {stats['overall_extraction_loss']:.2%}"
          + (f"  worst: {sorted(loss.items(), key=lambda kv: -kv[1])[:5]}" if loss else ""))
    if errors:
        print(f"{len(errors)} synthetic docs failed, e.g. {errors[0]['error']}")
    for p in real_problems[:20]:
        print(f"  label warning: {p}")


if __name__ == "__main__":
    main()
