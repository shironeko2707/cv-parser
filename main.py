"""
CV Parser Pipeline — Batch orchestrator.
Processes PDF/DOCX files into unified JSON format.

Usage:
    # Single file
    python main.py resume.pdf

    # Batch (directory)
    python main.py ./cv_folder/ --output ./output/

    # Batch with concurrency control
    python main.py ./cv_folder/ --output ./output/ --workers 8
"""
import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from schema_loader import load_schema
from text_extractor import extract
from ai_extractor import extract_fields
from picklist_mapper import PicklistMapper
from json_assembler import assemble_json, to_json_string


def parse_single_cv(filepath: str) -> dict:
    """
    Parse a single CV file end-to-end.
    Takes schema_data as a serializable dict (for multiprocessing).
    Returns a result dict with status, data, and diagnostics.
    """
    start = time.time()
    result = {
        "file": filepath,
        "status": "success",
        "data": None,
        "fields_extracted": 0,
        "missing_required": [],
        "confidence_scores": {},
        "warnings": [],
        "elapsed_ms": 0,
    }

    try:
        # Reload schema in each worker process
        schema = load_schema()
        mapper = PicklistMapper(schema)

        # Step 1: Extract text/layout from PDF/DOCX
        doc = extract(filepath)

        # Step 2: AI-based field extraction via self-hosted LLM
        fields = extract_fields(doc, schema=schema)

        # Step 3: Assemble JSON (picklist resolution, date normalization, field ordering)
        json_data = assemble_json(fields, schema, mapper)

        # Diagnostics
        candidate = json_data[0] if json_data else {}
        all_keys = set()
        _collect_keys(candidate, all_keys)
        result["fields_extracted"] = len(all_keys) - 1  # exclude __metadata

        # Check required fields
        required = [f for f in schema.top_level_fields if f.required]
        for f in required:
            if f.field_id not in candidate:
                result["missing_required"].append(f.field_id)

        result["confidence_scores"] = fields.confidence
        result["data"] = json_data

        if result["missing_required"]:
            result["warnings"].append(
                f"Missing {len(result['missing_required'])} required fields: "
                + ", ".join(result["missing_required"])
            )

    except Exception as e:
        result["status"] = "error"
        result["warnings"].append(f"{type(e).__name__}: {e}")
        result["data"] = None

    result["elapsed_ms"] = int((time.time() - start) * 1000)
    return result


def _collect_keys(obj: dict, keys: set, prefix: str = ""):
    for k, v in obj.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict) and "results" in v:
            for item in v["results"]:
                if isinstance(item, dict):
                    _collect_keys(item, keys, full_key)


def run_batch(input_dir: str, output_dir: str, workers: int = 4):
    """Process all CV files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = []
    for ext in ("*.pdf", "*.PDF", "*.docx", "*.DOCX", "*.doc"):
        files.extend(input_path.glob(ext))

    if not files:
        print(f"No CV files found in {input_dir}")
        return

    print(f"Found {len(files)} CV files. Processing with {workers} workers...")
    print("-" * 70)

    results_summary = {"success": 0, "error": 0, "total_fields": 0, "total_time_ms": 0}
    batch_start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for f in files:
            future = executor.submit(parse_single_cv, str(f))
            futures[future] = f

        for future in as_completed(futures):
            filepath = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {
                    "file": str(filepath),
                    "status": "error",
                    "warnings": [f"Worker error: {e}"],
                    "data": None,
                    "fields_extracted": 0,
                    "elapsed_ms": 0,
                }

            # Status indicator
            status_icon = "OK" if result["status"] == "success" else "ERR"
            filename = Path(result["file"]).name
            print(
                f"  [{status_icon}] {filename:<40} "
                f"fields={result['fields_extracted']:<3} "
                f"time={result['elapsed_ms']}ms"
            )
            if result["warnings"]:
                for w in result["warnings"]:
                    print(f"        -> {w}")

            # Save output
            if result["data"]:
                stem = Path(result["file"]).stem
                out_file = output_path / f"{stem}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(to_json_string(result["data"]))

            results_summary["success" if result["status"] == "success" else "error"] += 1
            results_summary["total_fields"] += result["fields_extracted"]
            results_summary["total_time_ms"] += result["elapsed_ms"]

    total_time = int((time.time() - batch_start) * 1000)
    print("-" * 70)
    print(f"Done! {results_summary['success']}/{len(files)} succeeded, "
          f"{results_summary['error']} errors")
    print(f"Total fields extracted: {results_summary['total_fields']} "
          f"(avg {results_summary['total_fields'] / max(len(files), 1):.1f}/file)")
    print(f"Total time: {total_time}ms "
          f"(avg {total_time / max(len(files), 1):.0f}ms/file)")

    # Write summary report
    report_path = output_path / "_batch_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "total_files": len(files),
            "success": results_summary["success"],
            "errors": results_summary["error"],
            "avg_fields_per_file": round(results_summary["total_fields"] / max(len(files), 1), 1),
            "total_time_ms": total_time,
            "avg_time_per_file_ms": round(total_time / max(len(files), 1)),
        }, f, indent=2)
    print(f"Report saved to {report_path}")


def run_single(filepath: str, output: str | None = None):
    """Process a single CV file."""
    result = parse_single_cv(filepath)

    if result["status"] == "error":
        print(f"Error processing {filepath}:", file=sys.stderr)
        for w in result["warnings"]:
            print(f"  {w}", file=sys.stderr)
        sys.exit(1)

    json_str = to_json_string(result["data"])

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Output saved to {output}")
    else:
        print(json_str)

    print(f"\n--- Diagnostics ---", file=sys.stderr)
    print(f"Fields extracted: {result['fields_extracted']}", file=sys.stderr)
    if result["missing_required"]:
        print(f"Missing required: {', '.join(result['missing_required'])}", file=sys.stderr)
    if result["confidence_scores"]:
        low_conf = {k: v for k, v in result["confidence_scores"].items() if v < 0.7}
        if low_conf:
            print(f"Low confidence: {low_conf}", file=sys.stderr)
    print(f"Time: {result['elapsed_ms']}ms", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CV Parser Pipeline")
    parser.add_argument("input", help="CV file (pdf/docx) or directory for batch mode")
    parser.add_argument("--output", "-o", help="Output file (single) or directory (batch)")
    parser.add_argument("--workers", "-w", type=int, default=1,
                        help="Number of parallel workers for batch mode (default: 1, LLM is sequential)")
    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_dir():
        output_dir = args.output or str(input_path / "output")
        run_batch(str(input_path), output_dir, args.workers)
    elif input_path.is_file():
        run_single(str(input_path), args.output)
    else:
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
