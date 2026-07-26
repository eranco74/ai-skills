#!/usr/bin/env python3
"""
Evaluation orchestrator for the prd-creator.

Runs the PRD generation pipeline against eval dataset cases,
scores the results using deterministic checks, and produces
a summary report.

Usage:
    python3 scripts/run_eval.py [--cases CASE1 CASE2 ...]
    python3 scripts/run_eval.py --all
    python3 scripts/run_eval.py --report  # Just report on existing results
"""

import argparse
import json
import os
import re
import subprocess
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path


CASES_DIR = Path("eval/dataset/cases")
ARTIFACTS_DIR = Path("artifacts")
RESULTS_DIR = Path("eval/results")


def load_case(case_id: str) -> dict:
    """Load a test case's input and annotations."""
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        print(f"Error: Case {case_id} not found at {case_dir}", file=sys.stderr)
        return None

    result = {"case_id": case_id}

    input_file = case_dir / "input.yaml"
    if input_file.exists():
        with open(input_file) as f:
            result["input"] = yaml.safe_load(f)

    annotations_file = case_dir / "annotations.yaml"
    if annotations_file.exists():
        with open(annotations_file) as f:
            result["annotations"] = yaml.safe_load(f)

    gold_prd = case_dir / "gold-prd.md"
    if gold_prd.exists():
        result["gold_prd"] = gold_prd.read_text()

    return result


def list_cases() -> list:
    """List all available eval cases."""
    if not CASES_DIR.exists():
        return []
    return sorted([d.name for d in CASES_DIR.iterdir() if d.is_dir()])


def run_deterministic_checks(prd_path: str) -> dict:
    """Run all deterministic scoring checks on a PRD."""
    results = {}

    for check in ["check-structure", "check-personas", "check-leakage"]:
        try:
            proc = subprocess.run(
                ["python3", "scripts/score_prd.py", check, prd_path],
                capture_output=True, text=True, timeout=30
            )
            results[check] = json.loads(proc.stdout) if proc.stdout.strip() else {
                "pass": False, "issues": [f"No output from {check}"]
            }
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            results[check] = {"pass": False, "issues": [str(e)]}

    return results


def compare_with_gold(generated_path: str, gold_path: str) -> dict:
    """Compare generated PRD with gold standard using heuristics."""
    gen_text = Path(generated_path).read_text()
    gold_text = Path(gold_path).read_text()

    gen_sections = set()
    gold_sections = set()

    for line in gen_text.split("\n"):
        m = re.match(r"^##\s+(?:\d+\.?\s*)?(.+)$", line)
        if m:
            gen_sections.add(m.group(1).strip().lower())

    for line in gold_text.split("\n"):
        m = re.match(r"^##\s+(?:\d+\.?\s*)?(.+)$", line)
        if m:
            gold_sections.add(m.group(1).strip().lower())

    common = gen_sections & gold_sections
    missing = gold_sections - gen_sections
    extra = gen_sections - gold_sections

    gen_personas = set()
    gold_personas = set()
    for persona in ["Cloud Provider Admin", "Cloud Infrastructure Admin", "Tenant Admin", "Tenant User"]:
        if persona in gen_text:
            gen_personas.add(persona)
        if persona in gold_text:
            gold_personas.add(persona)

    gen_lines = len([l for l in gen_text.split("\n") if l.strip()])
    gold_lines = len([l for l in gold_text.split("\n") if l.strip()])
    length_ratio = gen_lines / max(gold_lines, 1)

    return {
        "section_overlap": len(common) / max(len(gold_sections), 1),
        "missing_sections": list(missing),
        "extra_sections": list(extra),
        "persona_overlap": len(gen_personas & gold_personas) / max(len(gold_personas), 1),
        "missing_personas": list(gold_personas - gen_personas),
        "length_ratio": round(length_ratio, 2),
        "gen_lines": gen_lines,
        "gold_lines": gold_lines,
    }


def score_case(case: dict, prd_path: str) -> dict:
    """Score a single case's generated PRD."""
    result = {
        "case_id": case["case_id"],
        "jira_key": case["input"].get("jira_key", "unknown"),
        "title": case["input"].get("title", "unknown"),
        "expected_score": case.get("annotations", {}).get("expected_score"),
        "prd_exists": Path(prd_path).exists(),
    }

    if not result["prd_exists"]:
        result["checks"] = {"error": "PRD file not generated"}
        result["overall_pass"] = False
        return result

    result["checks"] = run_deterministic_checks(prd_path)

    all_pass = all(c.get("pass", False) for c in result["checks"].values())
    result["checks_pass"] = all_pass

    gold_path = CASES_DIR / case["case_id"] / "gold-prd.md"
    if gold_path.exists():
        result["gold_comparison"] = compare_with_gold(prd_path, str(gold_path))

    review_path = ARTIFACTS_DIR / "prd-reviews" / f"{case['input']['jira_key']}-review.md"
    if review_path.exists():
        content = review_path.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if fm and isinstance(fm, dict):
                    result["review_score"] = fm.get("score")
                    result["review_pass"] = fm.get("pass")
                    result["review_recommendation"] = fm.get("recommendation")
                    result["review_scores"] = fm.get("scores", {})
            except yaml.YAMLError:
                pass

    return result


def generate_report(results: list, iteration: int = 1) -> str:
    """Generate a human-readable evaluation report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"# PRD Creator Evaluation Report — Iteration {iteration}",
        f"",
        f"**Date:** {timestamp}",
        f"**Cases:** {len(results)}",
        f"",
        "## Summary",
        "",
        "| Case | Jira | Expected | Generated | Structure | Personas | Leakage | Gold Overlap |",
        "|------|------|----------|-----------|-----------|----------|---------|--------------|",
    ]

    total_structure = 0
    total_persona = 0
    total_leakage = 0
    total_gold_overlap = 0.0
    gold_count = 0

    for r in results:
        jira = r.get("jira_key", "?")
        expected = r.get("expected_score", "?")
        generated = r.get("review_score", "?")
        struct = "PASS" if r.get("checks", {}).get("check-structure", {}).get("pass") else "FAIL"
        persona = "PASS" if r.get("checks", {}).get("check-personas", {}).get("pass") else "FAIL"
        leak = "PASS" if r.get("checks", {}).get("check-leakage", {}).get("pass") else "FAIL"
        gold_ovlp = r.get("gold_comparison", {}).get("section_overlap", 0)
        gold_str = f"{gold_ovlp:.0%}" if gold_ovlp else "N/A"

        if struct == "PASS":
            total_structure += 1
        if persona == "PASS":
            total_persona += 1
        if leak == "PASS":
            total_leakage += 1
        if gold_ovlp:
            total_gold_overlap += gold_ovlp
            gold_count += 1

        lines.append(f"| {r['case_id']} | {jira} | {expected}/10 | {generated}/10 | {struct} | {persona} | {leak} | {gold_str} |")

    lines.extend([
        "",
        "## Aggregate Metrics",
        "",
        f"- **Structure pass rate:** {total_structure}/{len(results)} ({total_structure/max(len(results),1):.0%})",
        f"- **Persona coverage pass rate:** {total_persona}/{len(results)} ({total_persona/max(len(results),1):.0%})",
        f"- **No-leakage pass rate:** {total_leakage}/{len(results)} ({total_leakage/max(len(results),1):.0%})",
        f"- **Avg gold section overlap:** {total_gold_overlap/max(gold_count,1):.0%} (across {gold_count} cases)",
    ])

    review_scores = [r.get("review_score") for r in results if r.get("review_score") is not None]
    if review_scores:
        avg_score = sum(review_scores) / len(review_scores)
        pass_count = sum(1 for r in results if r.get("review_pass"))
        lines.extend([
            f"- **Avg review score:** {avg_score:.1f}/10",
            f"- **Review pass rate:** {pass_count}/{len(review_scores)} ({pass_count/max(len(review_scores),1):.0%})",
        ])

    lines.extend([
        "",
        "## Per-Case Details",
        "",
    ])

    for r in results:
        lines.append(f"### {r['case_id']} — {r.get('title', 'Unknown')}")
        lines.append("")

        if not r.get("prd_exists"):
            lines.append("**PRD not generated.**")
            lines.append("")
            continue

        for check_name, check_result in r.get("checks", {}).items():
            status = "PASS" if check_result.get("pass") else "FAIL"
            lines.append(f"- **{check_name}:** {status}")
            for issue in check_result.get("issues", []):
                lines.append(f"  - {issue}")

        gold = r.get("gold_comparison", {})
        if gold:
            lines.append(f"- **Gold comparison:**")
            lines.append(f"  - Section overlap: {gold.get('section_overlap', 0):.0%}")
            lines.append(f"  - Persona overlap: {gold.get('persona_overlap', 0):.0%}")
            lines.append(f"  - Length: {gold.get('gen_lines', 0)} lines (gold: {gold.get('gold_lines', 0)})")
            if gold.get("missing_sections"):
                lines.append(f"  - Missing sections: {', '.join(gold['missing_sections'])}")
            if gold.get("missing_personas"):
                lines.append(f"  - Missing personas: {', '.join(gold['missing_personas'])}")

        if r.get("review_scores"):
            lines.append(f"- **Review scores:** {r['review_scores']}")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run PRD creator evaluation")
    parser.add_argument("--cases", nargs="+", help="Specific case IDs to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all cases")
    parser.add_argument("--report", action="store_true", help="Generate report from existing results")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration number for report")
    args = parser.parse_args()

    os.chdir(Path(__file__).parent.parent)

    if args.cases:
        case_ids = args.cases
    elif args.all or args.report:
        case_ids = list_cases()
    else:
        print("Usage: python3 scripts/run_eval.py --all")
        print("       python3 scripts/run_eval.py --cases OSAC-1269 OSAC-2917")
        print("       python3 scripts/run_eval.py --report")
        sys.exit(1)

    if not case_ids:
        print("No cases found.", file=sys.stderr)
        sys.exit(1)

    print(f"Evaluating {len(case_ids)} cases...", file=sys.stderr)

    results = []
    for case_id in case_ids:
        case = load_case(case_id)
        if not case:
            continue

        jira_key = case["input"]["jira_key"]
        prd_path = str(ARTIFACTS_DIR / "prd-tasks" / f"{jira_key}.md")

        result = score_case(case, prd_path)
        results.append(result)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(results, iteration=args.iteration)
    report_path = RESULTS_DIR / f"report-iter{args.iteration}.md"
    report_path.write_text(report)
    print(f"Report written to {report_path}", file=sys.stderr)

    results_path = RESULTS_DIR / f"results-iter{args.iteration}.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))

    print(report)


if __name__ == "__main__":
    main()
