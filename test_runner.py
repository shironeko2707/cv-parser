"""
CV Parsing Test Runner
======================
Compares your parser's JSON output against ground truth, scores each field,
and produces a per-CV + aggregate report.

Usage:
    python test_runner.py --parsed_dir ./parsed/ --truth_dir ./ground_truth/

    The parsed directory should contain cv01.json … cv10.json produced by
    your parser.  The truth directory ships with this test suite.

Scoring overview:
    - Each CV is scored on every field present in ground truth.
    - Fields are weighted by importance (CRITICAL > IMPORTANT > NICE_TO_HAVE).
    - String fields use fuzzy matching (Levenshtein ratio).
    - List fields use set-overlap (Jaccard + best-match pairing).
    - Nested objects recurse.
    - A CV passes if its weighted score >= PASS_THRESHOLD (default 0.80).
    - The suite passes if >= 8/10 CVs pass AND mean score >= 0.75.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

# ============================================================
# CONFIGURATION
# ============================================================

PASS_THRESHOLD_PER_CV = 0.80       # 80 % weighted score to pass one CV
SUITE_PASS_MIN_CVS    = 8          # at least 8/10 CVs must pass
SUITE_PASS_MIN_MEAN   = 0.75       # overall mean must be >= 75 %
FUZZY_MATCH_THRESHOLD = 0.80       # string similarity floor for "match"

# Weight tiers for fields
CRITICAL     = 3.0   # must-extract fields
IMPORTANT    = 2.0   # strongly expected
NICE_TO_HAVE = 1.0   # bonus if captured

# Map: dotted path → weight.  Anything not listed defaults to NICE_TO_HAVE.
FIELD_WEIGHTS: dict[str, float] = {
    # ---- personal_info ----
    "personal_info.full_name":       CRITICAL,
    "personal_info.email":           CRITICAL,
    "personal_info.phone":           CRITICAL,
    "personal_info.date_of_birth":   IMPORTANT,
    "personal_info.gender":          IMPORTANT,
    "personal_info.nationality":     IMPORTANT,
    "personal_info.address":         IMPORTANT,
    "personal_info.city":            IMPORTANT,
    "personal_info.country":         IMPORTANT,
    "personal_info.linkedin":        NICE_TO_HAVE,
    "personal_info.github":          NICE_TO_HAVE,
    "personal_info.portfolio":       NICE_TO_HAVE,
    "personal_info.id_number":       IMPORTANT,
    "personal_info.preferred_name":  NICE_TO_HAVE,
    "personal_info.marital_status":  NICE_TO_HAVE,
    "personal_info.emergency_contact": NICE_TO_HAVE,

    # ---- position_applied ----
    "position_applied.title":           CRITICAL,
    "position_applied.department":      IMPORTANT,
    "position_applied.reference_number": IMPORTANT,
    "position_applied.expected_salary":  IMPORTANT,
    "position_applied.available_from":   NICE_TO_HAVE,
    "position_applied.notice_period":    NICE_TO_HAVE,

    # ---- current_employment ----
    "current_employment.employee_id":        CRITICAL,
    "current_employment.department":         IMPORTANT,
    "current_employment.position":           CRITICAL,
    "current_employment.branch":             IMPORTANT,
    "current_employment.direct_manager":     IMPORTANT,
    "current_employment.grade_level":        NICE_TO_HAVE,
    "current_employment.performance_rating": NICE_TO_HAVE,
    "current_employment.date_of_joining":    NICE_TO_HAVE,
    "current_employment.years_in_role":      NICE_TO_HAVE,

    # ---- top-level sections ----
    "summary":          IMPORTANT,
    "education":        CRITICAL,
    "work_experience":  CRITICAL,
    "skills":           IMPORTANT,
    "certifications":   IMPORTANT,
    "languages":        IMPORTANT,
    "publications":     IMPORTANT,
    "projects":         NICE_TO_HAVE,
    "awards":           NICE_TO_HAVE,
    "patents":          NICE_TO_HAVE,
    "references":       NICE_TO_HAVE,
    "activities":       NICE_TO_HAVE,
    "metadata":         NICE_TO_HAVE,
}


# ============================================================
# SCORING HELPERS
# ============================================================

def normalize(s: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation edges."""
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def fuzzy_score(a: str, b: str) -> float:
    """SequenceMatcher ratio on normalized strings."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def best_pair_score(truth_list: list[str], parsed_list: list[str]) -> float:
    """
    For two lists of strings, find the best 1-to-1 pairing by fuzzy score.
    Returns (matched_count / truth_count).
    """
    if not truth_list:
        return 1.0
    if not parsed_list:
        return 0.0

    used = set()
    matched = 0
    for t in truth_list:
        best, best_idx = 0.0, -1
        for i, p in enumerate(parsed_list):
            if i in used:
                continue
            sc = fuzzy_score(t, p)
            if sc > best:
                best, best_idx = sc, i
        if best >= FUZZY_MATCH_THRESHOLD and best_idx >= 0:
            used.add(best_idx)
            matched += 1
    return matched / len(truth_list)


def score_value(truth: Any, parsed: Any, path: str = "") -> tuple[float, list[str]]:
    """
    Compare a single ground-truth value against the parsed value.
    Returns (score 0..1, list_of_issues).
    """
    issues: list[str] = []

    # --- missing ---
    if parsed is None:
        issues.append(f"MISSING  {path}")
        return 0.0, issues

    # --- both are dicts ---
    if isinstance(truth, dict) and isinstance(parsed, dict):
        return score_dict(truth, parsed, path)

    # --- both are lists ---
    if isinstance(truth, list) and isinstance(parsed, list):
        return score_list(truth, parsed, path)

    # --- scalar: bool ---
    if isinstance(truth, bool):
        sc = 1.0 if parsed == truth else 0.0
        if sc < 1:
            issues.append(f"WRONG    {path}: expected={truth}, got={parsed}")
        return sc, issues

    # --- scalar: string ---
    if isinstance(truth, str):
        if not isinstance(parsed, str):
            parsed = str(parsed)
        sc = fuzzy_score(truth, parsed)
        if sc < FUZZY_MATCH_THRESHOLD:
            issues.append(f"MISMATCH {path}: expected='{truth[:60]}', got='{str(parsed)[:60]}' (sim={sc:.2f})")
        return sc, issues

    # --- fallback ---
    sc = 1.0 if truth == parsed else 0.0
    if sc < 1:
        issues.append(f"WRONG    {path}: expected={truth}, got={parsed}")
    return sc, issues


def score_dict(truth: dict, parsed: dict, prefix: str = "") -> tuple[float, list[str]]:
    """Score every key in truth against parsed.  Returns weighted average."""
    if not truth:
        return 1.0, []

    total_w, total_s = 0.0, 0.0
    all_issues: list[str] = []

    for key, tval in truth.items():
        path = f"{prefix}.{key}" if prefix else key
        w = FIELD_WEIGHTS.get(path, NICE_TO_HAVE)
        pval = parsed.get(key)
        sc, iss = score_value(tval, pval, path)
        total_w += w
        total_s += w * sc
        all_issues.extend(iss)

    return (total_s / total_w if total_w else 1.0), all_issues


def score_list(truth: list, parsed: list, path: str) -> tuple[float, list[str]]:
    """Score a list field.  Strategy depends on element type."""
    issues: list[str] = []
    if not truth:
        return 1.0, []
    if not parsed:
        issues.append(f"EMPTY    {path}: expected {len(truth)} items, got 0")
        return 0.0, issues

    # ---- list of strings (skills, activities) ----
    if all(isinstance(x, str) for x in truth):
        sc = best_pair_score(truth, [str(x) for x in parsed])
        if sc < 1.0:
            issues.append(f"PARTIAL  {path}: matched {sc*100:.0f}% of {len(truth)} items")
        return sc, issues

    # ---- list of dicts (education, experience, etc.) ----
    if all(isinstance(x, dict) for x in truth):
        # Count-level check
        count_ratio = min(len(parsed), len(truth)) / len(truth)
        if len(parsed) < len(truth):
            issues.append(f"SHORT    {path}: expected {len(truth)} entries, got {len(parsed)}")

        # Pair by best match on "key" fields
        entry_scores = []
        used = set()
        for ti, tentry in enumerate(truth):
            best_sc, best_idx = -1.0, -1
            for pi, pentry in enumerate(parsed):
                if pi in used or not isinstance(pentry, dict):
                    continue
                sc, _ = score_dict(tentry, pentry, f"{path}[{ti}]")
                if sc > best_sc:
                    best_sc, best_idx = sc, pi
            if best_idx >= 0:
                used.add(best_idx)
                sc, iss = score_dict(tentry, parsed[best_idx], f"{path}[{ti}]")
                entry_scores.append(sc)
                issues.extend(iss)
            else:
                entry_scores.append(0.0)
                issues.append(f"MISSING  {path}[{ti}]: no matching entry found")

        avg = sum(entry_scores) / len(entry_scores) if entry_scores else 0.0
        # Blend: 70% content accuracy + 30% count accuracy
        final = 0.7 * avg + 0.3 * count_ratio
        return final, issues

    # fallback
    return (1.0 if truth == parsed else 0.5), issues


# ============================================================
# REPORT
# ============================================================

@dataclass
class CVResult:
    cv_id: str
    score: float
    passed: bool
    issues: list[str] = field(default_factory=list)
    field_scores: dict[str, float] = field(default_factory=dict)


def evaluate_cv(cv_id: str, truth: dict, parsed: dict) -> CVResult:
    """Run full evaluation for one CV."""
    score, issues = score_dict(truth, parsed)
    passed = score >= PASS_THRESHOLD_PER_CV

    # Per-section breakdown
    field_scores = {}
    for section in truth:
        if section == "metadata":
            continue
        pval = parsed.get(section)
        if pval is None:
            field_scores[section] = 0.0
        else:
            sc, _ = score_value(truth[section], pval, section)
            field_scores[section] = round(sc, 3)

    return CVResult(cv_id=cv_id, score=round(score, 4),
                    passed=passed, issues=issues, field_scores=field_scores)


def print_report(results: list[CVResult]):
    """Pretty-print the full test report."""
    W = 80
    print("=" * W)
    print("  CV PARSING TEST REPORT".center(W))
    print("=" * W)
    print()

    passed_count = sum(1 for r in results if r.passed)
    mean_score = sum(r.score for r in results) / len(results) if results else 0

    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        bar_len = int(r.score * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"  {r.cv_id}  {status}  [{bar}] {r.score*100:5.1f}%")

        # Section breakdown
        if r.field_scores:
            parts = [f"{k}={v*100:.0f}%" for k, v in r.field_scores.items()]
            print(f"           Sections: {', '.join(parts)}")

        # Issues (show top 5 per CV)
        if r.issues:
            shown = r.issues[:5]
            for iss in shown:
                print(f"           ⚠ {iss}")
            if len(r.issues) > 5:
                print(f"           … and {len(r.issues)-5} more issues")
        print()

    # ---- SUITE SUMMARY ----
    print("-" * W)
    print(f"  CVs passed:    {passed_count} / {len(results)}  (threshold: {SUITE_PASS_MIN_CVS})")
    print(f"  Mean score:    {mean_score*100:.1f}%  (threshold: {SUITE_PASS_MIN_MEAN*100:.0f}%)")
    suite_pass = (passed_count >= SUITE_PASS_MIN_CVS and mean_score >= SUITE_PASS_MIN_MEAN)
    print()
    if suite_pass:
        print("  ✅  SUITE PASSED")
    else:
        print("  ❌  SUITE FAILED")
        if passed_count < SUITE_PASS_MIN_CVS:
            print(f"       → Need {SUITE_PASS_MIN_CVS} CVs passing, only got {passed_count}")
        if mean_score < SUITE_PASS_MIN_MEAN:
            print(f"       → Need {SUITE_PASS_MIN_MEAN*100:.0f}% mean score, got {mean_score*100:.1f}%")
    print("=" * W)

    # ---- SECTION HEATMAP ----
    all_sections = sorted({s for r in results for s in r.field_scores})
    if all_sections:
        print()
        print("  SECTION HEATMAP (avg score across CVs that have the section)")
        print("  " + "-" * (W - 4))
        for sec in all_sections:
            scores = [r.field_scores[sec] for r in results if sec in r.field_scores]
            if scores:
                avg = sum(scores) / len(scores)
                bar_len = int(avg * 30)
                bar = "█" * bar_len + "░" * (30 - bar_len)
                print(f"    {sec:<25s} [{bar}] {avg*100:5.1f}%  (n={len(scores)})")
        print()

    return suite_pass


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test CV parser output against ground truth"
    )
    parser.add_argument(
        "--parsed_dir", required=True,
        help="Directory containing your parser output: cv01.json … cv10.json"
    )
    parser.add_argument(
        "--truth_dir", default=os.path.join(os.path.dirname(__file__), "ground_truth"),
        help="Directory containing ground truth JSON (default: ./ground_truth/)"
    )
    parser.add_argument(
        "--threshold", type=float, default=PASS_THRESHOLD_PER_CV,
        help=f"Per-CV pass threshold (default: {PASS_THRESHOLD_PER_CV})"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show all issues, not just top 5 per CV"
    )
    parser.add_argument(
        "--json-report", type=str, default=None,
        help="Write machine-readable JSON report to this path"
    )
    args = parser.parse_args()

    threshold = args.threshold

    cv_ids = [f"cv{i:02d}" for i in range(1, 11)]
    results: list[CVResult] = []

    for cv_id in cv_ids:
        truth_path = os.path.join(args.truth_dir, f"{cv_id}.json")
        parsed_path = os.path.join(args.parsed_dir, f"{cv_id}.json")

        if not os.path.exists(truth_path):
            print(f"⚠ Ground truth not found: {truth_path}, skipping {cv_id}")
            continue

        if not os.path.exists(parsed_path):
            print(f"⚠ Parsed output not found: {parsed_path}")
            results.append(CVResult(
                cv_id=cv_id, score=0.0, passed=False,
                issues=[f"FILE NOT FOUND: {parsed_path}"]
            ))
            continue

        with open(truth_path) as f:
            truth = json.load(f)
        with open(parsed_path) as f:
            parsed = json.load(f)

        result = evaluate_cv(cv_id, truth, parsed)
        result.passed = result.score >= threshold
        results.append(result)

    suite_pass = print_report(results)

    # Optional JSON report
    if args.json_report:
        report = {
            "suite_passed": suite_pass,
            "mean_score": round(sum(r.score for r in results) / len(results), 4) if results else 0,
            "cvs_passed": sum(1 for r in results if r.passed),
            "cvs_total": len(results),
            "results": [
                {
                    "cv_id": r.cv_id,
                    "score": r.score,
                    "passed": r.passed,
                    "field_scores": r.field_scores,
                    "issues": r.issues,
                }
                for r in results
            ]
        }
        with open(args.json_report, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n  JSON report saved to: {args.json_report}")

    sys.exit(0 if suite_pass else 1)


if __name__ == "__main__":
    main()
