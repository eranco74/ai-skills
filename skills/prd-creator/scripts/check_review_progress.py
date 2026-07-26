#!/usr/bin/env python3
"""
Check progress of PRD generation/review agents.

Polls artifact files on disk to determine which IDs have completed
each phase (generate, review, revise).

Usage:
    python3 scripts/check_review_progress.py --phase generate --id-file FILE
    python3 scripts/check_review_progress.py --phase review --id-file FILE
    python3 scripts/check_review_progress.py --phase revise --id-file FILE
    python3 scripts/check_review_progress.py --wait --id-file FILE
"""

import argparse
import json
import sys
import time
import yaml
from pathlib import Path


def check_generate(prd_id):
    return Path(f"artifacts/prd-tasks/{prd_id}.md").exists()


def check_review(prd_id):
    review_path = Path(f"artifacts/prd-reviews/{prd_id}-review.md")
    if not review_path.exists():
        return False
    content = review_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1])
        return fm and "score" in fm
    except yaml.YAMLError:
        return False


def check_revise(prd_id):
    review_path = Path(f"artifacts/prd-reviews/{prd_id}-review.md")
    if not review_path.exists():
        return False
    content = review_path.read_text()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1])
        return fm and fm.get("auto_revised", False)
    except yaml.YAMLError:
        return False


PHASE_CHECKS = {
    "generate": check_generate,
    "review": check_review,
    "revise": check_revise,
    "reassess_review": check_review,
    "reassess_revise": check_revise,
}


def main():
    parser = argparse.ArgumentParser(description="Check PRD agent progress")
    parser.add_argument("--phase", choices=list(PHASE_CHECKS.keys()),
                        help="Phase to check")
    parser.add_argument("--id-file", required=True, help="File with IDs to check")
    parser.add_argument("--wait", action="store_true",
                        help="Wait mode: poll until all complete (max 5 min)")
    args = parser.parse_args()

    id_path = Path(args.id_file)
    if not id_path.exists():
        print("ID file not found", file=sys.stderr)
        sys.exit(1)

    ids = [line.strip() for line in id_path.read_text().splitlines() if line.strip()]
    if not ids:
        print("COMPLETED=0/0", file=sys.stderr)
        sys.exit(0)

    if args.wait:
        phases_to_check = list(PHASE_CHECKS.keys()) if not args.phase else [args.phase]
    else:
        phases_to_check = [args.phase] if args.phase else ["generate"]

    check_fn = PHASE_CHECKS.get(phases_to_check[0], check_generate)

    completed = []
    pending = []
    for prd_id in ids:
        if check_fn(prd_id):
            completed.append(prd_id)
        else:
            pending.append(prd_id)

    status = {
        "completed": len(completed),
        "pending": len(pending),
        "total": len(ids),
        "completed_ids": completed,
        "pending_ids": pending,
    }

    print(f"COMPLETED={len(completed)}/{len(ids)}", file=sys.stderr)

    if pending:
        print(f"PENDING: {', '.join(pending[:5])}" +
              (f" (+{len(pending)-5} more)" if len(pending) > 5 else ""),
              file=sys.stderr)
        print(f"NEXT_POLL=15", file=sys.stderr)
        sys.exit(3 if args.wait else 0)
    else:
        print("All complete.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
