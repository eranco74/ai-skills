#!/usr/bin/env python3
"""
Evaluate a Forge-generated PRD against OSAC quality standards.

Works on any PRD markdown file — doesn't need Forge, pipeline_state.py,
or any prd-creator infrastructure. Just point it at a prd.md.

Usage:
    # Score a single PRD
    python3 eval_forge_prd.py path/to/prd.md

    # Score against a gold standard
    python3 eval_forge_prd.py path/to/prd.md --gold path/to/gold-prd.md

    # Score a PR directly
    python3 eval_forge_prd.py --pr 181 --repo osac-project/enhancement-proposals

    # Run all eval cases
    python3 eval_forge_prd.py --all
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_SECTIONS = ["Problem Statement", "In Scope", "Out of Scope", "User Stories"]
OPTIONAL_SECTIONS = ["Assumptions", "Dependencies"]
FORBIDDEN_SECTIONS = [
    "Risks", "Acceptance Criteria", "Terminology", "Milestone",
    "Open Questions", "Success Metrics", "Goals", "Non-Goals",
    "Requirements", "Functional Requirements",
]
PERSONAS = [
    "Cloud Provider Admin", "Cloud Infrastructure Admin",
    "Tenant Admin", "Tenant User",
]
LEAKAGE_PATTERNS = [
    (r'\breconcil(?:er?|ation)\b', 'reconciler/reconciliation'),
    (r'\bfinalizer\b', 'finalizer'),
    (r'\bplaybook\b', 'playbook'),
    (r'\bAAP job\b', 'AAP job'),
    (r'\bosac-operator\b', 'osac-operator'),
    (r'\bosac-aap\b', 'osac-aap'),
    (r'\bcontroller\b(?!\s+Planes?)', 'controller'),
    (r'\bInfraEnv\b', 'InfraEnv'),
    (r'\bSQLSTATE\b', 'SQLSTATE'),
    (r'status=True', 'condition spec'),
    (r'reason=\w+Completed', 'condition reason'),
    (r'exponential backoff', 'retry implementation'),
    (r'\benv var\b', 'env var'),
]


def extract_headings(content):
    return [m.group(1).strip() for m in re.finditer(r'^##\s+(.+)$', content, re.MULTILINE)]


def check_template(content):
    headings = extract_headings(content)
    heading_lower = [h.lower() for h in headings]

    missing = [s for s in REQUIRED_SECTIONS
               if not any(s.lower() in h for h in heading_lower)]
    extra = [h for h in headings
             if any(f.lower() in h.lower() for f in FORBIDDEN_SECTIONS)]

    return {
        "pass": len(missing) == 0 and len(extra) == 0,
        "missing": missing,
        "extra": extra,
        "headings": headings,
    }


def check_personas(content):
    found = [p for p in PERSONAS if p in content]
    missing = [p for p in PERSONAS if p not in content]
    return {
        "pass": len(found) >= 2,
        "found": found,
        "missing": missing,
    }


def check_leakage(content):
    found = []
    for pattern, label in LEAKAGE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            found.append(f"{label} ({len(matches)}x)")
    return {
        "pass": len(found) == 0,
        "leakage": found,
    }


def check_length(content):
    non_blank = len([l for l in content.split("\n") if l.strip()])
    return {
        "pass": 10 <= non_blank <= 120,
        "lines": non_blank,
        "assessment": "too long" if non_blank > 120 else "too short" if non_blank < 10 else "ok",
    }


def compare_with_gold(generated, gold):
    gen_headings = set(h.lower() for h in extract_headings(generated))
    gold_headings = set(h.lower() for h in extract_headings(gold))

    gen_personas = set(p for p in PERSONAS if p in generated)
    gold_personas = set(p for p in PERSONAS if p in gold)

    gen_lines = len([l for l in generated.split("\n") if l.strip()])
    gold_lines = len([l for l in gold.split("\n") if l.strip()])

    return {
        "section_overlap": len(gen_headings & gold_headings) / max(len(gold_headings), 1),
        "missing_sections": list(gold_headings - gen_headings),
        "extra_sections": list(gen_headings - gold_headings),
        "persona_overlap": len(gen_personas & gold_personas) / max(len(gold_personas), 1),
        "length_ratio": round(gen_lines / max(gold_lines, 1), 2),
        "gen_lines": gen_lines,
        "gold_lines": gold_lines,
    }


def fetch_pr_prd(pr_number, repo):
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number), "--repo", repo],
            capture_output=True, text=True, check=True
        )
        lines = []
        in_prd = False
        for line in result.stdout.split("\n"):
            if line.startswith("+++ b/") and "prd.md" in line:
                in_prd = True
                continue
            if line.startswith("+++ b/") and in_prd:
                break
            if in_prd and line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])
        return "\n".join(lines)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR: {e}", file=sys.stderr)
        sys.exit(1)


def score_prd(content, gold_content=None):
    results = {
        "template": check_template(content),
        "personas": check_personas(content),
        "leakage": check_leakage(content),
        "length": check_length(content),
    }

    if gold_content:
        results["gold_comparison"] = compare_with_gold(content, gold_content)

    all_pass = all(r["pass"] for r in results.values() if "pass" in r)
    results["overall_pass"] = all_pass

    return results


def print_report(results, prd_source):
    print(f"## Forge PRD Evaluation: {prd_source}")
    print()

    checks = [
        ("Template compliance", results["template"]),
        ("Persona coverage", results["personas"]),
        ("Design leakage", results["leakage"]),
        ("Length", results["length"]),
    ]

    print("| Check | Result | Details |")
    print("|-------|--------|---------|")
    for name, r in checks:
        status = "PASS" if r["pass"] else "FAIL"
        if name == "Template compliance":
            details = []
            if r["missing"]:
                details.append(f"missing: {', '.join(r['missing'])}")
            if r["extra"]:
                details.append(f"extra: {', '.join(r['extra'])}")
            detail = "; ".join(details) if details else f"{len(r['headings'])} sections"
        elif name == "Persona coverage":
            detail = f"found: {', '.join(r['found'])}" if r["found"] else "none found"
        elif name == "Design leakage":
            detail = ", ".join(r["leakage"]) if r["leakage"] else "clean"
        elif name == "Length":
            detail = f"{r['lines']} lines ({r['assessment']})"
        print(f"| {name} | {status} | {detail} |")

    print()

    if "gold_comparison" in results:
        g = results["gold_comparison"]
        print(f"### Gold Comparison")
        print(f"- Section overlap: {g['section_overlap']:.0%}")
        print(f"- Persona overlap: {g['persona_overlap']:.0%}")
        print(f"- Length: {g['gen_lines']} lines (gold: {g['gold_lines']})")
        if g["extra_sections"]:
            print(f"- Extra sections: {', '.join(g['extra_sections'])}")
        print()

    overall = "PASS" if results["overall_pass"] else "FAIL"
    print(f"**Overall: {overall}**")


def main():
    parser = argparse.ArgumentParser(description="Evaluate a Forge-generated PRD")
    parser.add_argument("prd_file", nargs="?", help="Path to PRD markdown file")
    parser.add_argument("--gold", help="Path to gold-standard PRD for comparison")
    parser.add_argument("--pr", type=int, help="PR number to fetch PRD from")
    parser.add_argument("--repo", default="osac-project/enhancement-proposals")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    args = parser.parse_args()

    if args.pr:
        content = fetch_pr_prd(args.pr, args.repo)
        source = f"PR #{args.pr}"
    elif args.prd_file:
        content = Path(args.prd_file).read_text()
        source = args.prd_file
    else:
        print("Provide a PRD file path or --pr NUMBER", file=sys.stderr)
        sys.exit(1)

    gold_content = Path(args.gold).read_text() if args.gold else None

    results = score_prd(content, gold_content)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, source)

    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()
