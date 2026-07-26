#!/usr/bin/env python3
"""Bridge prd-creator artifacts into ai-workflows layout for provenance tracking.

Usage:
    python3 scripts/bridge_artifacts.py {JIRA_KEY} [--docs-repo PATH]

Creates .artifacts/prd/{KEY}/ directory structure and calls provenance capture.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def workspace_root() -> Path:
    """Find workspace root by traversing up to find .git or .artifacts."""
    current = Path.cwd()
    for _ in range(32):
        if (current / ".git").is_dir() or (current / ".artifacts").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd()


def get_docs_repo_remote(docs_repo_path: Path) -> str:
    """Get origin remote URL from the docs repo."""
    try:
        result = subprocess.run(
            ["git", "-C", str(docs_repo_path), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"Warning: Could not get docs repo remote: {exc}", file=sys.stderr)
        return "unknown"


def bridge_artifacts(jira_key: str, docs_repo_path: Path | None = None) -> int:
    """Bridge prd-creator artifacts into ai-workflows layout."""
    root = workspace_root()
    prd_tasks_dir = root / "artifacts" / "prd-tasks"
    artifacts_dir = root / ".artifacts" / "prd" / jira_key

    # Verify source files exist
    prd_file = prd_tasks_dir / f"{jira_key}.md"
    source_file = prd_tasks_dir / f"{jira_key}-source.md"

    if not prd_file.is_file():
        print(f"Error: PRD file not found: {prd_file}", file=sys.stderr)
        return 1

    # Create artifacts directory
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Copy PRD to 03-prd.md
    shutil.copy2(prd_file, artifacts_dir / "03-prd.md")
    print(f"Copied {prd_file} → {artifacts_dir / '03-prd.md'}")

    # Copy source to 01-requirements.md if exists
    if source_file.is_file():
        shutil.copy2(source_file, artifacts_dir / "01-requirements.md")
        print(f"Copied {source_file} → {artifacts_dir / '01-requirements.md'}")
    else:
        print(f"Warning: Source file not found, skipping: {source_file}", file=sys.stderr)

    # Determine docs repo path
    if docs_repo_path is None:
        # Default to enhancement-proposals in parent workspace
        docs_repo_path = root.parent / "enhancement-proposals"

    if not docs_repo_path.is_dir():
        print(f"Warning: docs repo not found at {docs_repo_path}", file=sys.stderr)
        docs_remote = "unknown"
    else:
        docs_remote = get_docs_repo_remote(docs_repo_path)

    # Create config.json
    config_path = root / ".artifacts" / "prd" / "config.json"
    config = {
        "docs_repo_path": str(docs_repo_path.resolve()),
        "docs_repo_remote": docs_remote,
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote config: {config_path}")

    # Capture provenance
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if not provenance_script.is_file():
        print(f"Warning: provenance script not found: {provenance_script}", file=sys.stderr)
        print("Skipping provenance capture", file=sys.stderr)
        return 0

    try:
        subprocess.run(
            [
                "python3",
                str(provenance_script),
                "capture",
                "--workflow", "prd",
                "--issue", jira_key,
                "--phase", "draft",
                "--authoring-mode", "skill",
            ],
            check=True,
            timeout=30,
        )
        print(f"Captured provenance: prd/{jira_key} phase=draft")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"Warning: provenance capture failed: {exc}", file=sys.stderr)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge prd-creator artifacts into ai-workflows layout")
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument(
        "--docs-repo",
        type=Path,
        help="Path to enhancement-proposals repo (default: ../enhancement-proposals)",
    )
    args = parser.parse_args()

    try:
        return bridge_artifacts(args.jira_key, args.docs_repo)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
