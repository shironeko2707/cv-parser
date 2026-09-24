"""
Automated validation of CV parser output.
Checks schema compliance, format correctness, and structural completeness.
No ground truth needed — runs purely on the output JSON + schema.

Usage:
    python auto_validator.py output.json
    python auto_validator.py output_folder/
    python auto_validator.py output_folder/ --report validation_report.json
"""
import argparse
import json
import re
import sys
from pathlib import Path
from schema_loader import load_schema, Schema

schema = load_schema()

VALID_TOP_LEVEL_IDS = {fd.field_id for fd in schema.top_level_fields}
VALID_SECTION_KEYS = {}
for sec_name, fds in schema.sections.items():
    VALID_SECTION_KEYS[sec_name] = {fd.nested_key for fd in fds if fd.nested_key}

REQUIRED_FIELDS = [fd.field_id for fd in schema.top_level_fields if fd.required]

PICKLIST_FIELDS = {
    fd.field_id: fd.picklist_id
    for fd in schema.top_level_fields
    if fd.field_type == "Picklist" and fd.picklist_id
}

DATE_FIELDS = {fd.field_id for fd in schema.top_level_fields if fd.field_type == "DateTime"}

SECTION_DATE_KEYS = {}
SECTION_PICKLIST_KEYS = {}
for sec_name, fds in schema.sections.items():
    SECTION_DATE_KEYS[sec_name] = {fd.nested_key for fd in fds if fd.field_type == "DateTime" and fd.nested_key}
    SECTION_PICKLIST_KEYS[sec_name] = {
        fd.nested_key: fd.picklist_id
        for fd in fds
        if fd.field_type == "Picklist" and fd.picklist_id and fd.nested_key
    }

SECTION_REQUIRED_KEYS = {
    "education": ["degree", "school"],
    "outsideWorkExperience": ["startTitle", "employer"],
    "languages": ["language"],
    "certificates": ["name"],
    "awards": ["name"],
    "courses": ["name"],
    "familyMember": ["firstName"],
}

DATE_RE = re.compile(r"^/Date\(-?\d+\)/$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"[\d\s\-\+\(\)]{7,}")


def validate_file(filepath: str) -> dict:
    """Validate a single JSON output file. Returns a report dict."""
    report = {
        "file": Path(filepath).name,
        "valid": True,
        "issues": [],
        "stats": {
            "top_level_fields": 0,
            "sections_present": [],
            "total_section_entries": 0,
            "required_present": 0,
            "required_total": len(REQUIRED_FIELDS),
            "dates_valid": 0,
            "dates_total": 0,
            "picklists_resolved": 0,
            "picklists_total": 0,
            "unknown_fields": [],
            "unknown_section_keys": [],
        },
    }
    issues = report["issues"]
    stats = report["stats"]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        report["valid"] = False
        issues.append(f"Cannot read file: {e}")
        return report

    if not isinstance(data, list) or not data:
        report["valid"] = False
        issues.append("Expected non-empty JSON array")
        return report

    candidate = data[0]
    if not isinstance(candidate, dict):
        report["valid"] = False
        issues.append("First element is not a JSON object")
        return report

    # --- Top-level field checks ---
    for key, value in candidate.items():
        if key == "__metadata":
            continue
        if isinstance(value, dict) and "results" in value:
            continue
        if key not in VALID_TOP_LEVEL_IDS:
            stats["unknown_fields"].append(key)
        else:
            stats["top_level_fields"] += 1

    if stats["unknown_fields"]:
        issues.append(f"Unknown top-level fields: {stats['unknown_fields']}")

    # --- Required fields ---
    for fid in REQUIRED_FIELDS:
        if fid in candidate:
            stats["required_present"] += 1
        else:
            issues.append(f"Missing required field: {fid}")

    # --- Date format ---
    for fid in DATE_FIELDS:
        if fid in candidate:
            stats["dates_total"] += 1
            val = candidate[fid]
            if isinstance(val, str) and DATE_RE.match(val):
                stats["dates_valid"] += 1
            else:
                issues.append(f"Invalid date format for '{fid}': {val}")

    # --- Picklist resolution ---
    for fid, pid in PICKLIST_FIELDS.items():
        if fid in candidate:
            stats["picklists_total"] += 1
            val = candidate[fid]
            if isinstance(val, dict) and "id" in val:
                stats["picklists_resolved"] += 1
            elif isinstance(val, str) and val.isdigit():
                stats["picklists_resolved"] += 1
            else:
                issues.append(f"Picklist not resolved for '{fid}': {val}")

    # --- Email format ---
    for fid in ("primaryEmail", "contactEmail"):
        if fid in candidate:
            if not EMAIL_RE.match(str(candidate[fid])):
                issues.append(f"Invalid email format for '{fid}': {candidate[fid]}")

    # --- Phone format ---
    for fid in ("cellPhone", "homePhone"):
        if fid in candidate:
            if not PHONE_RE.search(str(candidate[fid])):
                issues.append(f"Suspicious phone format for '{fid}': {candidate[fid]}")

    # --- Section checks ---
    for sec_name, valid_keys in VALID_SECTION_KEYS.items():
        if sec_name not in candidate:
            continue

        sec = candidate[sec_name]
        if not isinstance(sec, dict) or "results" not in sec:
            issues.append(f"Section '{sec_name}' has wrong structure (expected {{results: [...]}})")
            continue

        entries = sec["results"]
        if not isinstance(entries, list) or not entries:
            issues.append(f"Section '{sec_name}' has empty results")
            continue

        stats["sections_present"].append(sec_name)
        stats["total_section_entries"] += len(entries)

        date_keys = SECTION_DATE_KEYS.get(sec_name, set())
        picklist_keys = SECTION_PICKLIST_KEYS.get(sec_name, {})
        required_keys = SECTION_REQUIRED_KEYS.get(sec_name, [])

        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                issues.append(f"{sec_name}[{i}]: not a dict")
                continue

            for k in entry:
                if k not in valid_keys:
                    stats["unknown_section_keys"].append(f"{sec_name}.{k}")

            for rk in required_keys:
                if rk not in entry or not entry[rk]:
                    issues.append(f"{sec_name}[{i}]: missing key '{rk}'")

            for k, v in entry.items():
                if k in date_keys:
                    stats["dates_total"] += 1
                    if isinstance(v, str) and DATE_RE.match(v):
                        stats["dates_valid"] += 1
                    else:
                        issues.append(f"{sec_name}[{i}].{k}: invalid date '{v}'")

                if k in picklist_keys:
                    stats["picklists_total"] += 1
                    if isinstance(v, str) and v.isdigit():
                        stats["picklists_resolved"] += 1
                    elif isinstance(v, dict) and "id" in v:
                        stats["picklists_resolved"] += 1
                    else:
                        issues.append(f"{sec_name}[{i}].{k}: picklist not resolved '{v}'")

    if stats["unknown_section_keys"]:
        issues.append(f"Unknown section keys: {stats['unknown_section_keys']}")

    # --- Name sanity ---
    fn = candidate.get("firstName", "")
    ln = candidate.get("lastName", "")
    if fn and ln and fn == ln:
        issues.append(f"firstName == lastName ('{fn}'), likely extraction error")

    for fid in ("firstName", "lastName"):
        val = candidate.get(fid, "")
        if val and ("@" in val or any(c.isdigit() for c in val)):
            issues.append(f"'{fid}' contains suspicious chars: {val}")

    if issues:
        report["valid"] = False

    return report


def print_report(report: dict):
    s = report["stats"]
    status = "PASS" if report["valid"] else "FAIL"
    print(f"  [{status}] {report['file']}")
    print(f"         Fields: {s['top_level_fields']} top-level, "
          f"{s['total_section_entries']} section entries "
          f"({', '.join(s['sections_present']) or 'none'})")
    print(f"         Required: {s['required_present']}/{s['required_total']}")

    dates_pct = f"{s['dates_valid']}/{s['dates_total']}" if s["dates_total"] else "n/a"
    pick_pct = f"{s['picklists_resolved']}/{s['picklists_total']}" if s["picklists_total"] else "n/a"
    print(f"         Dates: {dates_pct}  Picklists: {pick_pct}")

    if report["issues"]:
        for issue in report["issues"]:
            print(f"         ! {issue}")


def print_summary(reports: list[dict]):
    total = len(reports)
    passed = sum(1 for r in reports if r["valid"])
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} files passed validation")

    all_issues = {}
    for r in reports:
        for issue in r["issues"]:
            category = issue.split(":")[0] if ":" in issue else issue
            all_issues[category] = all_issues.get(category, 0) + 1

    if all_issues:
        print(f"\nMost common issues:")
        for cat, count in sorted(all_issues.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:3d}x  {cat}")

    agg_stats = {
        "total_files": total,
        "passed": passed,
        "failed": total - passed,
        "avg_top_level_fields": 0,
        "avg_section_entries": 0,
        "total_dates": 0,
        "valid_dates": 0,
        "total_picklists": 0,
        "resolved_picklists": 0,
        "required_fill_rate": 0,
    }
    for r in reports:
        s = r["stats"]
        agg_stats["avg_top_level_fields"] += s["top_level_fields"]
        agg_stats["avg_section_entries"] += s["total_section_entries"]
        agg_stats["total_dates"] += s["dates_total"]
        agg_stats["valid_dates"] += s["dates_valid"]
        agg_stats["total_picklists"] += s["picklists_total"]
        agg_stats["resolved_picklists"] += s["picklists_resolved"]
        agg_stats["required_fill_rate"] += s["required_present"]

    if total:
        agg_stats["avg_top_level_fields"] = round(agg_stats["avg_top_level_fields"] / total, 1)
        agg_stats["avg_section_entries"] = round(agg_stats["avg_section_entries"] / total, 1)
        agg_stats["required_fill_rate"] = round(
            agg_stats["required_fill_rate"] / (total * len(REQUIRED_FIELDS)) * 100, 1
        )

    date_pct = round(agg_stats["valid_dates"] / max(agg_stats["total_dates"], 1) * 100, 1)
    pick_pct = round(agg_stats["resolved_picklists"] / max(agg_stats["total_picklists"], 1) * 100, 1)

    print(f"\nAggregate metrics:")
    print(f"  Avg top-level fields:  {agg_stats['avg_top_level_fields']}")
    print(f"  Avg section entries:   {agg_stats['avg_section_entries']}")
    print(f"  Required fill rate:    {agg_stats['required_fill_rate']}%")
    print(f"  Date format valid:     {date_pct}% ({agg_stats['valid_dates']}/{agg_stats['total_dates']})")
    print(f"  Picklist resolved:     {pick_pct}% ({agg_stats['resolved_picklists']}/{agg_stats['total_picklists']})")

    return agg_stats


def main():
    parser = argparse.ArgumentParser(description="Validate CV parser JSON output")
    parser.add_argument("input", help="JSON file or directory of JSON files")
    parser.add_argument("--report", "-r", help="Save report to JSON file")
    args = parser.parse_args()

    input_path = Path(args.input)
    files = []
    if input_path.is_dir():
        files = sorted(input_path.glob("*.json"))
        files = [f for f in files if not f.name.startswith("_")]
    elif input_path.is_file():
        files = [input_path]
    else:
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    if not files:
        print("No JSON files found")
        sys.exit(1)

    print(f"Validating {len(files)} file(s)...\n")

    reports = []
    for f in files:
        report = validate_file(str(f))
        reports.append(report)
        print_report(report)
        print()

    agg = print_summary(reports)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump({
                "aggregate": agg,
                "files": [{
                    "file": r["file"],
                    "valid": r["valid"],
                    "issue_count": len(r["issues"]),
                    "issues": r["issues"],
                    "stats": r["stats"],
                } for r in reports],
            }, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to {args.report}")


if __name__ == "__main__":
    main()
