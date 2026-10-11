#!/usr/bin/env python3
"""Package one organizational research contract into each installed consumer."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "skills/_shared/context/organizational-research.md"
TARGETS = [
    ROOT / "skills/prd-creator/context/organizational-research.md",
    ROOT / "skills/design-creator/context/organizational-research.md",
    ROOT / "skills/prd-review/references/organizational-research.md",
    ROOT / "skills/design-review/references/organizational-research.md",
    ROOT / "forge-skills/osac/generate-prd/context/organizational-research.md",
    ROOT / "forge-skills/osac/generate-spec/context/organizational-research.md",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = SOURCE.read_bytes()
    stale = []
    for target in TARGETS:
        if args.check:
            if not target.exists() or target.read_bytes() != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    if stale:
        print("Research contract drift: " + ", ".join(stale))
        return 1
    print("Research contract copies match" if args.check else "Packaged research contract into six consumers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
