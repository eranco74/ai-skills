#!/usr/bin/env python3
"""
Evaluate a Forge-generated design document against OSAC quality standards.

Works on any design markdown file — doesn't need Forge, pipeline_state.py,
or any prd-creator infrastructure. Just point it at a design.md.

Usage:
    # Score a single PRD
    python3 eval_forge_design.py path/to/design.md

    # Score against a gold standard
    python3 eval_forge_design.py path/to/design.md --gold path/to/gold-design.md

    # Score a PR directly
    python3 eval_forge_design.py --pr 181 --repo osac-project/enhancement-proposals

    # Run all eval cases
    python3 eval_forge_design.py --all
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_SECTIONS = ["Summary", "Motivation", "Proposal", "Test Plan", "Alternatives"]
OPTIONAL_SECTIONS = ["Security Considerations", "Failure Handling", "RBAC", "Observability", "Risks", "Drawbacks", "Graduation Criteria", "Upgrade", "Version Skew", "Support Procedures"]
FORBIDDEN_SECTIONS = []  # Design template allows all sections
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
        "assessment": "too long" if non_blank > 900 else "too short" if non_blank < 100 else "ok",
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
            if line.startswith("+++ b/") and "design.md" in line:
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


def score_design(content, gold_content=None):
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
    print(f"## Forge Design Evaluation: {prd_source}")
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


def load_case(case_dir):
    """Load an eval case from a directory."""
    case_dir = Path(case_dir)
    case = {"case_id": case_dir.name}

    input_file = case_dir / "input.yaml"
    if input_file.exists():
        import yaml
        with open(input_file) as f:
            case["input"] = yaml.safe_load(f)

    annotations_file = case_dir / "annotations.yaml"
    if annotations_file.exists():
        import yaml
        with open(annotations_file) as f:
            case["annotations"] = yaml.safe_load(f)

    gold_file = case_dir / "gold-design.md"
    if gold_file.exists():
        case["gold_content"] = gold_file.read_text()

    return case


def run_all_cases(cases_dir, generated_dir=None, pr_numbers=None):
    """Run eval on all cases. Needs either generated files or PR numbers."""
    cases_dir = Path(cases_dir)
    results = []

    for case_path in sorted(cases_dir.iterdir()):
        if not case_path.is_dir():
            continue

        case = load_case(case_path)
        jira_key = case.get("input", {}).get("jira_key", case["case_id"])

        # Find the generated PRD
        content = None
        source = None

        # Option 1: generated file provided
        if generated_dir:
            for pattern in [f"{jira_key}.md", f"{jira_key}-design.md", f"{jira_key}/design.md"]:
                gen_path = Path(generated_dir) / pattern
                if gen_path.exists():
                    content = gen_path.read_text()
                    source = str(gen_path)
                    break

        # Option 2: PR number mapping
        if not content and pr_numbers and jira_key in pr_numbers:
            content = fetch_pr_prd(pr_numbers[jira_key], "osac-project/enhancement-proposals")
            source = f"PR #{pr_numbers[jira_key]}"

        if not content:
            results.append({
                "case_id": case["case_id"],
                "jira_key": jira_key,
                "title": case.get("input", {}).get("title", "?"),
                "expected_score": case.get("annotations", {}).get("expected_score"),
                "generated": False,
            })
            continue

        gold_content = case.get("gold_content")
        scored = score_design(content, gold_content)
        scored["case_id"] = case["case_id"]
        scored["jira_key"] = jira_key
        scored["title"] = case.get("input", {}).get("title", "?")
        scored["expected_score"] = case.get("annotations", {}).get("expected_score")
        scored["source"] = source
        scored["generated"] = True
        results.append(scored)

    return results


def print_all_report(results):
    """Print a summary report for all cases."""
    print("# Forge Design Evaluation Report")
    print()

    generated = [r for r in results if r.get("generated")]
    not_generated = [r for r in results if not r.get("generated")]

    print(f"**Cases:** {len(results)} total, {len(generated)} evaluated, {len(not_generated)} not generated")
    print()

    if generated:
        print("| Case | Jira | Expected | Template | Personas | Leakage | Length | Gold Overlap |")
        print("|------|------|----------|----------|----------|---------|--------|-------------|")

        for r in generated:
            jira = r.get("jira_key", "?")
            expected = r.get("expected_score", "?")
            template = "PASS" if r.get("template", {}).get("pass") else "FAIL"
            personas = "PASS" if r.get("personas", {}).get("pass") else "FAIL"
            leakage = "PASS" if r.get("leakage", {}).get("pass") else "FAIL"
            length = f"{r.get('length', {}).get('lines', '?')} lines"
            gold = f"{r.get('gold_comparison', {}).get('section_overlap', 0):.0%}" if "gold_comparison" in r else "N/A"
            print(f"| {r['case_id']} | {jira} | {expected}/10 | {template} | {personas} | {leakage} | {length} | {gold} |")

        print()

        # Aggregates
        template_pass = sum(1 for r in generated if r.get("template", {}).get("pass"))
        persona_pass = sum(1 for r in generated if r.get("personas", {}).get("pass"))
        leakage_pass = sum(1 for r in generated if r.get("leakage", {}).get("pass"))
        length_pass = sum(1 for r in generated if r.get("length", {}).get("pass"))
        n = len(generated)

        print("## Aggregate Metrics")
        print(f"- Template compliance: {template_pass}/{n} ({template_pass/n:.0%})")
        print(f"- Persona coverage: {persona_pass}/{n} ({persona_pass/n:.0%})")
        print(f"- No design leakage: {leakage_pass}/{n} ({leakage_pass/n:.0%})")
        print(f"- Length in range: {length_pass}/{n} ({length_pass/n:.0%})")
        print()

    if not_generated:
        print("## Not Generated")
        for r in not_generated:
            print(f"- {r['case_id']} ({r.get('jira_key', '?')}): no generated PRD found")
        print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate Forge-generated designs")
    parser.add_argument("design_file", nargs="?", help="Path to design markdown file")
    parser.add_argument("--gold", help="Path to gold-standard design for comparison")
    parser.add_argument("--pr", type=int, help="PR number to fetch PRD from")
    parser.add_argument("--repo", default="osac-project/enhancement-proposals")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--all", action="store_true", help="Run all eval cases")
    parser.add_argument("--cases-dir", default="eval/dataset/cases",
                        help="Path to eval cases directory")
    parser.add_argument("--generated-dir", help="Directory with generated PRD files")
    args = parser.parse_args()

    if args.all:
        results = run_all_cases(args.cases_dir, args.generated_dir)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print_all_report(results)
        all_pass = all(r.get("overall_pass", False) for r in results if r.get("generated"))
        sys.exit(0 if all_pass else 1)

    if args.pr:
        content = fetch_pr_prd(args.pr, args.repo)
        source = f"PR #{args.pr}"
    elif args.design_file:
        content = Path(args.design_file).read_text()
        source = args.design_file
    else:
        print("Provide a PRD file, --pr NUMBER, or --all", file=sys.stderr)
        sys.exit(1)

    gold_content = Path(args.gold).read_text() if args.gold else None

    results = score_design(content, gold_content)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, source)

    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()
