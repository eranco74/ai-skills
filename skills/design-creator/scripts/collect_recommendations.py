#!/usr/bin/env python3
"""
Collect review recommendations across all PRDs.

Groups PRDs by recommendation: SUBMIT, REVISE, REJECT, ERRORS.

Usage:
    python3 scripts/collect_recommendations.py [--ids-file FILE] [--reassess] [ID ...]
"""

import argparse
import sys
import yaml
from pathlib import Path


def get_review_data(prd_id):
    """Read review frontmatter for a PRD."""
    review_path = Path(f"artifacts/prd-reviews/{prd_id}-review.md")
    if not review_path.exists():
        return None
    content = review_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Collect PRD review recommendations")
    parser.add_argument("ids", nargs="*", help="PRD IDs to check")
    parser.add_argument("--ids-file", help="File containing IDs (one per line)")
    parser.add_argument("--reassess", action="store_true",
                        help="Output IDs needing reassessment (auto_revised=true, pass=false)")
    parser.add_argument("--errors", action="store_true",
                        help="Output IDs with errors (no review file or missing fields)")
    args = parser.parse_args()

    ids = list(args.ids)
    if args.ids_file:
        p = Path(args.ids_file)
        if p.exists():
            ids.extend(line.strip() for line in p.read_text().splitlines() if line.strip())

    if not ids:
        print("No IDs provided.", file=sys.stderr)
        sys.exit(1)

    submit = []
    revise = []
    reject = []
    errors = []
    reassess = []

    for prd_id in sorted(set(ids)):
        data = get_review_data(prd_id)
        if data is None:
            errors.append(prd_id)
            continue

        rec = data.get("recommendation", "")
        passed = data.get("pass", False)
        auto_revised = data.get("auto_revised", False)

        if args.reassess:
            if auto_revised and not passed:
                reassess.append(prd_id)
            continue

        if args.errors:
            if not data.get("score"):
                errors.append(prd_id)
            continue

        if rec == "submit" and passed:
            submit.append(prd_id)
        elif rec == "reject":
            reject.append(prd_id)
        elif rec == "revise" or (not passed and rec != "reject"):
            revise.append(prd_id)
        else:
            submit.append(prd_id)

    if args.reassess:
        print(f"REASSESS={','.join(reassess) if reassess else ''}")
        return

    if args.errors:
        print(f"ERRORS={','.join(errors) if errors else ''}")
        return

    print(f"SUBMIT={','.join(submit) if submit else ''}")
    print(f"REVISE={','.join(revise) if revise else ''}")
    print(f"REJECT={','.join(reject) if reject else ''}")
    print(f"ERRORS={','.join(errors) if errors else ''}")

    total = len(submit) + len(revise) + len(reject) + len(errors)
    print(f"\nSummary: {total} total | {len(submit)} submit | "
          f"{len(revise)} revise | {len(reject)} reject | {len(errors)} errors",
          file=sys.stderr)


if __name__ == "__main__":
    main()
