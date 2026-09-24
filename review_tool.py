"""
Human review tool for CV parser accuracy measurement.
Shows extracted fields side-by-side with CV text for manual verification.
Produces an anonymized accuracy report (percentages only, no PII values).

Usage:
    # Review a single file
    python review_tool.py cv.pdf output.json

    # Review a batch
    python review_tool.py cv_folder/ output_folder/

    # Resume interrupted review
    python review_tool.py cv_folder/ output_folder/ --resume

    # Generate report from saved reviews
    python review_tool.py --report review_results/
"""
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from text_extractor import extract


REVIEW_DIR = Path("review_results")

MARKS = {
    "y": "correct",
    "n": "wrong",
    "p": "partial",
    "s": "skip",
    "m": "missing",
}


def load_output(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) and data else data


def show_cv_text(cv_path: str) -> str:
    doc = extract(cv_path)
    text = doc.layout_text or doc.raw_text
    return text


def mask_value(value: str, show_chars: int = 4) -> str:
    """Partially mask a value for display during review."""
    if len(value) <= show_chars:
        return value
    return value[:show_chars] + "..." + value[-2:] if len(value) > show_chars + 2 else value[:show_chars] + "..."


def review_single(cv_path: str, json_path: str, resume: bool = False) -> dict | None:
    """Interactive review of one CV extraction result."""
    stem = Path(cv_path).stem
    result_file = REVIEW_DIR / f"{stem}_review.json"

    if resume and result_file.exists():
        print(f"  [skip] {stem} — already reviewed")
        with open(result_file) as f:
            return json.load(f)

    candidate = load_output(json_path)
    cv_text = show_cv_text(cv_path)

    print(f"\n{'='*70}")
    print(f"REVIEWING: {Path(cv_path).name}")
    print(f"{'='*70}")
    print(f"\n--- CV TEXT (first 2000 chars) ---")
    print(cv_text[:2000])
    print(f"\n{'='*70}")
    print("Mark each field:  [y]correct  [n]wrong  [p]partial  [s]skip  [q]quit")
    print(f"{'='*70}\n")

    review = {
        "file": stem,
        "reviewed_at": datetime.now().isoformat(),
        "fields": {},
        "sections": {},
    }

    # --- Top-level fields ---
    print("--- TOP-LEVEL FIELDS ---")
    for key, value in candidate.items():
        if key == "__metadata":
            continue
        if isinstance(value, dict) and "results" in value:
            continue

        display_val = str(value)
        if len(display_val) > 80:
            display_val = display_val[:80] + "..."

        while True:
            mark = input(f"  {key}: {display_val}  [y/n/p/s/q] ").strip().lower()
            if mark == "q":
                _save_review(review, result_file)
                print("Review saved (partial). Use --resume to continue later.")
                return review
            if mark in MARKS:
                review["fields"][key] = MARKS[mark]
                break
            print("    Invalid input. Use y/n/p/s/q")

    # --- Sections ---
    for sec_name, sec_data in candidate.items():
        if not isinstance(sec_data, dict) or "results" not in sec_data:
            continue

        entries = sec_data["results"]
        print(f"\n--- {sec_name.upper()} ({len(entries)} entries) ---")

        # First: is the entry count correct?
        while True:
            mark = input(f"  Entry count ({len(entries)}) correct? [y/n/p/s/q] ").strip().lower()
            if mark == "q":
                _save_review(review, result_file)
                return review
            if mark in MARKS:
                review["sections"].setdefault(sec_name, {})["_count"] = MARKS[mark]
                break
            print("    Invalid input.")

        for i, entry in enumerate(entries):
            print(f"\n  [{i}]:")
            entry_review = {}
            for k, v in entry.items():
                display_val = str(v)
                if len(display_val) > 80:
                    display_val = display_val[:80] + "..."
                while True:
                    mark = input(f"    {k}: {display_val}  [y/n/p/s/q] ").strip().lower()
                    if mark == "q":
                        _save_review(review, result_file)
                        return review
                    if mark in MARKS:
                        entry_review[k] = MARKS[mark]
                        break
                    print("      Invalid input.")
            review["sections"].setdefault(sec_name, {})[f"entry_{i}"] = entry_review

    _save_review(review, result_file)
    print(f"\nReview saved to {result_file}")
    return review


def _save_review(review: dict, path: Path):
    REVIEW_DIR.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)


def generate_report(review_dir: str) -> dict:
    """Generate anonymized accuracy report from saved reviews."""
    review_path = Path(review_dir)
    review_files = sorted(review_path.glob("*_review.json"))

    if not review_files:
        print("No review files found")
        return {}

    # Aggregate field-level accuracy
    field_stats: dict[str, dict[str, int]] = {}
    section_stats: dict[str, dict[str, dict[str, int]]] = {}
    count_stats: dict[str, dict[str, int]] = {}

    for rf in review_files:
        with open(rf) as f:
            review = json.load(f)

        for field_name, verdict in review.get("fields", {}).items():
            if verdict == "skip":
                continue
            field_stats.setdefault(field_name, {"correct": 0, "wrong": 0, "partial": 0, "total": 0})
            field_stats[field_name][verdict] = field_stats[field_name].get(verdict, 0) + 1
            field_stats[field_name]["total"] += 1

        for sec_name, sec_data in review.get("sections", {}).items():
            if "_count" in sec_data:
                verdict = sec_data["_count"]
                if verdict != "skip":
                    count_stats.setdefault(sec_name, {"correct": 0, "wrong": 0, "partial": 0, "total": 0})
                    count_stats[sec_name][verdict] = count_stats[sec_name].get(verdict, 0) + 1
                    count_stats[sec_name]["total"] += 1

            for entry_key, entry_data in sec_data.items():
                if entry_key == "_count" or not isinstance(entry_data, dict):
                    continue
                for field_name, verdict in entry_data.items():
                    if verdict == "skip":
                        continue
                    full_key = f"{sec_name}.{field_name}"
                    section_stats.setdefault(sec_name, {})
                    section_stats[sec_name].setdefault(field_name, {"correct": 0, "wrong": 0, "partial": 0, "total": 0})
                    section_stats[sec_name][field_name][verdict] = \
                        section_stats[sec_name][field_name].get(verdict, 0) + 1
                    section_stats[sec_name][field_name]["total"] += 1

    # Build report
    report = {
        "generated_at": datetime.now().isoformat(),
        "files_reviewed": len(review_files),
        "top_level_accuracy": {},
        "section_count_accuracy": {},
        "section_field_accuracy": {},
        "overall": {},
    }

    total_correct = 0
    total_partial = 0
    total_wrong = 0
    total_all = 0

    print(f"\n{'='*60}")
    print(f"ACCURACY REPORT — {len(review_files)} files reviewed")
    print(f"{'='*60}")

    print(f"\n--- TOP-LEVEL FIELDS ---")
    print(f"{'Field':<25} {'Correct':>8} {'Partial':>8} {'Wrong':>8} {'Acc%':>6}")
    print("-" * 60)

    for field_name in sorted(field_stats.keys()):
        s = field_stats[field_name]
        acc = round((s["correct"] + s["partial"] * 0.5) / max(s["total"], 1) * 100, 1)
        report["top_level_accuracy"][field_name] = {
            "correct": s["correct"],
            "partial": s["partial"],
            "wrong": s["wrong"],
            "total": s["total"],
            "accuracy_pct": acc,
        }
        total_correct += s["correct"]
        total_partial += s["partial"]
        total_wrong += s["wrong"]
        total_all += s["total"]
        print(f"  {field_name:<23} {s['correct']:>8} {s['partial']:>8} {s['wrong']:>8} {acc:>5.1f}%")

    for sec_name in sorted(section_stats.keys()):
        print(f"\n--- {sec_name.upper()} ---")
        if sec_name in count_stats:
            cs = count_stats[sec_name]
            cacc = round((cs["correct"] + cs["partial"] * 0.5) / max(cs["total"], 1) * 100, 1)
            print(f"  {'(entry count)':<23} {cs['correct']:>8} {cs['partial']:>8} {cs['wrong']:>8} {cacc:>5.1f}%")
            report["section_count_accuracy"][sec_name] = {"accuracy_pct": cacc, **cs}

        print(f"  {'Field':<23} {'Correct':>8} {'Partial':>8} {'Wrong':>8} {'Acc%':>6}")
        print("  " + "-" * 56)

        report["section_field_accuracy"].setdefault(sec_name, {})
        for field_name in sorted(section_stats[sec_name].keys()):
            s = section_stats[sec_name][field_name]
            acc = round((s["correct"] + s["partial"] * 0.5) / max(s["total"], 1) * 100, 1)
            report["section_field_accuracy"][sec_name][field_name] = {
                "accuracy_pct": acc, **s,
            }
            total_correct += s["correct"]
            total_partial += s["partial"]
            total_wrong += s["wrong"]
            total_all += s["total"]
            print(f"  {field_name:<23} {s['correct']:>8} {s['partial']:>8} {s['wrong']:>8} {acc:>5.1f}%")

    overall_acc = round((total_correct + total_partial * 0.5) / max(total_all, 1) * 100, 1)
    report["overall"] = {
        "total_fields_reviewed": total_all,
        "correct": total_correct,
        "partial": total_partial,
        "wrong": total_wrong,
        "accuracy_pct": overall_acc,
    }

    print(f"\n{'='*60}")
    print(f"OVERALL: {overall_acc}% accuracy ({total_correct} correct, "
          f"{total_partial} partial, {total_wrong} wrong / {total_all} total)")
    print(f"{'='*60}")

    report_file = review_path / "_accuracy_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nAnonymized report saved to {report_file}")
    print("(This report contains NO PII — safe to share for analysis)")

    return report


def main():
    parser = argparse.ArgumentParser(description="Human review tool for CV parser accuracy")
    parser.add_argument("input", nargs="?", help="CV file/folder")
    parser.add_argument("output", nargs="?", help="JSON output file/folder")
    parser.add_argument("--resume", action="store_true", help="Skip already reviewed files")
    parser.add_argument("--report", metavar="DIR", help="Generate report from review results directory")
    args = parser.parse_args()

    if args.report:
        generate_report(args.report)
        return

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_file() and output_path.is_file():
        review_single(str(input_path), str(output_path), resume=args.resume)
        print("\nRun with --report review_results/ to generate accuracy report")

    elif input_path.is_dir() and output_path.is_dir():
        cv_files = []
        for ext in ("*.pdf", "*.PDF", "*.docx", "*.DOCX"):
            cv_files.extend(sorted(input_path.glob(ext)))

        reviewed = 0
        for cv_file in cv_files:
            json_file = output_path / f"{cv_file.stem}.json"
            if not json_file.exists():
                print(f"  [skip] {cv_file.name} — no matching JSON output")
                continue

            result = review_single(str(cv_file), str(json_file), resume=args.resume)
            if result:
                reviewed += 1

        print(f"\nReviewed {reviewed}/{len(cv_files)} files")
        print(f"Run:  python review_tool.py --report review_results/")
    else:
        print("Error: both input and output must be files, or both directories")
        sys.exit(1)


if __name__ == "__main__":
    main()
