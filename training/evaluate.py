"""
Field-level evaluation of an SLM endpoint on held-out samples.

    # base model vs fine-tuned model, same data
    python -m training.evaluate --data data/val.jsonl --model gemma4:e2b --out eval_base.json
    python -m training.evaluate --data data/val.jsonl --model cv-parser --out eval_ft.json
    python -m training.evaluate --data data/val_real.jsonl --model cv-parser     # real CVs

The prediction goes through the production path (parse -> coerce -> ground),
so the numbers are what main.py would deliver. Reported per field:
precision / recall / F1 (normalized text match; exact match for dates/enums),
plus entry-count accuracy per section, JSON validity and latency.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rapidfuzz import fuzz  # noqa: E402

from canonical import (  # noqa: E402
    DATE_FIELDS, ENTRY_KEY_FIELDS, ENUM_FIELDS, SECTION_FIELDS, coerce, find_hints, ground, order_canonical,
)
from text_utils import digits_only, normalize_for_match  # noqa: E402


def values_match(field: str, gold: str, pred: str) -> bool:
    if field in DATE_FIELDS or field in ENUM_FIELDS:
        return gold.strip().lower() == pred.strip().lower()
    if field == "phone":
        return digits_only(gold)[-9:] == digits_only(pred)[-9:]
    g, p = normalize_for_match(gold), normalize_for_match(pred)
    if g == p:
        return True
    threshold = 85 if field == "description" else 92
    return fuzz.ratio(g, p) >= threshold


def pair_entries(section: str, gold: list[dict], pred: list[dict]) -> list[tuple[int, int]]:
    """Greedy one-to-one pairing of entries by their identifying fields."""
    keys = ENTRY_KEY_FIELDS[section]
    scores = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(pred):
            s = [fuzz.ratio(normalize_for_match(g.get(k, "")), normalize_for_match(p.get(k, "")))
                 for k in keys if g.get(k) or p.get(k)]
            if s:
                scores.append((sum(s) / len(s), gi, pi))
    pairs, used_g, used_p = [], set(), set()
    for score, gi, pi in sorted(scores, reverse=True):
        if score >= 60 and gi not in used_g and pi not in used_p:
            pairs.append((gi, pi))
            used_g.add(gi)
            used_p.add(pi)
    return pairs


def score_sample(gold: dict, pred: dict, counts: dict):
    """Accumulate TP/FP/FN per field path into counts[path] = [tp, fp, fn]."""
    gp, pp = gold.get("personal", {}), pred.get("personal", {})
    for k in set(gp) | set(pp):
        c = counts[f"personal.{k}"]
        if k in gp and k in pp:
            if values_match(k, gp[k], pp[k]):
                c[0] += 1
            else:
                c[1] += 1
                c[2] += 1
        elif k in pp:
            c[1] += 1
        else:
            c[2] += 1
    for sec in SECTION_FIELDS:
        g_list, p_list = gold.get(sec, []), pred.get(sec, [])
        cnt = counts[f"{sec}._count"]
        cnt[0 if len(g_list) == len(p_list) else 1] += 1
        pairs = pair_entries(sec, g_list, p_list)
        paired_g = {gi for gi, _ in pairs}
        paired_p = {pi for _, pi in pairs}
        for gi, pi in pairs:
            g, p = g_list[gi], p_list[pi]
            for f in set(g) | set(p):
                c = counts[f"{sec}.{f}"]
                if f in g and f in p:
                    if values_match(f, g[f], p[f]):
                        c[0] += 1
                    else:
                        c[1] += 1
                        c[2] += 1
                elif f in p:
                    c[1] += 1
                else:
                    c[2] += 1
        for gi, g in enumerate(g_list):
            if gi not in paired_g:
                for f in g:
                    counts[f"{sec}.{f}"][2] += 1
        for pi, p in enumerate(p_list):
            if pi not in paired_p:
                for f in p:
                    counts[f"{sec}.{f}"][1] += 1


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def cv_text_from_prompt(messages: list[dict]) -> str:
    user = next(m["content"] for m in messages if m["role"] == "user")
    if "<<<\n" in user and "\n>>>" in user:
        return user.split("<<<\n", 1)[1].rsplit("\n>>>", 1)[0]
    return user


def load_samples(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if "messages" in r:
                prompt, answer = r["messages"][:-1], r["messages"][-1]["content"]
            else:
                prompt, answer = r["prompt"], r["completion"][0]["content"]
            rows.append({"prompt": prompt, "gold": json.loads(answer), "meta": r.get("meta", {})})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="val.jsonl / val_real.jsonl from build_dataset")
    ap.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint (default: LLM_BASE_URL)")
    ap.add_argument("--model", default=None, help="model name (default: LLM_MODEL)")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1, help="parallel requests (if the server has slots)")
    ap.add_argument("--structured", default=None, help="json_schema | json | off (default: LLM_STRUCTURED)")
    ap.add_argument("--no-ground", action="store_true", help="score raw model output (no grounding/repair)")
    ap.add_argument("--out", default=None, help="write JSON report here")
    args = ap.parse_args()

    from ai_extractor import call_llm, parse_llm_json

    samples = load_samples(args.data)
    if args.limit:
        samples = samples[:args.limit]
    llm_kwargs = {k: v for k, v in {"base_url": args.base_url, "model": args.model, "api_key": args.api_key,
                                    "structured": args.structured}.items() if v}

    def run(sample):
        t0 = time.time()
        try:
            raw = call_llm(sample["prompt"], **llm_kwargs)
        except Exception as e:
            return {"error": str(e), "latency": time.time() - t0}
        latency = time.time() - t0
        try:
            pred = coerce(parse_llm_json(raw))
            valid = True
        except ValueError:
            pred, valid = {"personal": {}}, False
        if not args.no_ground:
            text = cv_text_from_prompt(sample["prompt"])
            pred, _ = ground(pred, text, find_hints(text))
        return {"pred": order_canonical(pred), "valid": valid, "latency": latency}

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(run, samples))

    counts: dict = defaultdict(lambda: [0, 0, 0])
    errors = [r["error"] for r in results if "error" in r]
    per_sample = []
    for sample, res in zip(samples, results):
        if "error" in res:
            continue
        sc: dict = defaultdict(lambda: [0, 0, 0])
        score_sample(sample["gold"], res["pred"], sc)
        for k, v in sc.items():
            for i in range(3):
                counts[k][i] += v[i]
        tp = sum(v[0] for k, v in sc.items() if not k.endswith("._count"))
        fp = sum(v[1] for k, v in sc.items() if not k.endswith("._count"))
        fn = sum(v[2] for k, v in sc.items() if not k.endswith("._count"))
        per_sample.append({"id": sample["meta"].get("id"), "f1": prf(tp, fp, fn)[2],
                           "template": sample["meta"].get("template")})

    fields = {k: v for k, v in counts.items() if not k.endswith("._count")}
    tp, fp, fn = (sum(v[i] for v in fields.values()) for i in range(3))
    micro = prf(tp, fp, fn)
    ok = [r for r in results if "error" not in r]
    report = {
        "data": args.data, "model": args.model, "samples": len(samples), "errors": len(errors),
        "json_valid_rate": round(sum(r["valid"] for r in ok) / max(len(ok), 1), 4),
        "avg_latency_s": round(sum(r["latency"] for r in ok) / max(len(ok), 1), 2),
        "wall_time_s": round(time.time() - t0, 1),
        "micro": {"precision": round(micro[0], 4), "recall": round(micro[1], 4), "f1": round(micro[2], 4)},
        "fields": {k: dict(zip(("precision", "recall", "f1"), (round(x, 4) for x in prf(*v))), support=v[0] + v[2])
                   for k, v in sorted(fields.items())},
        "entry_count_accuracy": {k[:-7]: round(v[0] / max(v[0] + v[1], 1), 4)
                                 for k, v in sorted(counts.items()) if k.endswith("._count")},
        "worst_samples": sorted(per_sample, key=lambda s: s["f1"])[:10],
        "error_examples": errors[:5],
    }
    by_template = defaultdict(list)
    for s in per_sample:
        by_template[s["template"] or "real"].append(s["f1"])
    report["f1_by_template"] = {t: round(sum(v) / len(v), 4) for t, v in sorted(by_template.items())}

    print(f"\nModel: {args.model or '(LLM_MODEL)'}   samples: {len(samples)}   errors: {len(errors)}")
    print(f"JSON valid: {report['json_valid_rate']:.1%}   avg latency: {report['avg_latency_s']}s")
    print(f"Micro  P={micro[0]:.3f}  R={micro[1]:.3f}  F1={micro[2]:.3f}\n")
    print(f"{'field':34} {'P':>6} {'R':>6} {'F1':>6} {'n':>6}")
    for k, v in report["fields"].items():
        if v["support"]:
            print(f"{k:34} {v['precision']:6.3f} {v['recall']:6.3f} {v['f1']:6.3f} {v['support']:6}")
    print("\nEntry-count accuracy:", report["entry_count_accuracy"])
    print("F1 by template:", report["f1_by_template"])
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
