#!/usr/bin/env python3
"""Apply design reviewer feedback and update the PR."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return Path.cwd()


def respond_design(jira_key: str, dry_run: bool = False) -> int:
    """Apply design reviewer feedback and update the PR.

    Args:
        jira_key: The Jira issue key (e.g., OSAC-1234)
        dry_run: If True, print actions without executing

    Returns:
        0 on success, 1 on error
    """
    root = repo_root()

    # Read the updated design
    design_file = root / ".artifacts" / "design" / jira_key / "03-design.md"
    if not design_file.exists():
        print(f"Error: Design file not found: {design_file}", file=sys.stderr)
        return 1

    design_content = design_file.read_text(encoding="utf-8")

    # Read publish metadata to get feature location
    metadata_file = root / ".artifacts" / "design" / jira_key / "publish-metadata.json"
    if not metadata_file.exists():
        print(f"Error: Publish metadata not found: {metadata_file}", file=sys.stderr)
        print("Run publish_design.py first", file=sys.stderr)
        return 1

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    feature_dir_name = metadata["feature_dir"]
    branch_name = metadata["branch_name"]

    # Read docs repo config
    config_file = root / ".artifacts" / "prd" / "config.json"
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        return 1

    config = json.loads(config_file.read_text(encoding="utf-8"))
    docs_repo_path = Path(config["docs_repo_path"])

    if not docs_repo_path.exists():
        print(f"Error: Docs repo not found: {docs_repo_path}", file=sys.stderr)
        return 1

    feature_dir = docs_repo_path / "enhancements" / feature_dir_name
    design_target = feature_dir / "design.md"

    print(f"\nRespond plan:")
    print(f"  Design file: {design_file}")
    print(f"  Target file: {design_target}")
    print(f"  Branch: {branch_name}")
    print(f"  Docs repo: {docs_repo_path}")

    if dry_run:
        print("\nDry run mode - no changes made")
        return 0

    # Switch to branch
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "checkout", branch_name],
            check=True,
            timeout=30,
        )
        print(f"Switched to branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error switching to branch: {e}", file=sys.stderr)
        return 1

    # Capture provenance for respond phase
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if provenance_script.exists():
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(provenance_script),
                    "capture",
                    "--workflow", "design",
                    "--issue", jira_key,
                    "--phase", "respond",
                    "--authoring-mode", "skill",
                ],
                check=True,
                cwd=str(root),
                timeout=30,
            )
            print(f"Captured provenance: design/{jira_key} phase=respond")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not capture provenance: {e}", file=sys.stderr)

    # Render provenance footer into the updated design
    if provenance_script.exists():
        # First copy the updated design
        design_target.write_text(design_content, encoding="utf-8")

        try:
            subprocess.run(
                [
                    sys.executable,
                    str(provenance_script),
                    "render",
                    "--workflow", "design",
                    "--issue", jira_key,
                    "--target", str(design_target),
                ],
                check=True,
                cwd=str(root),
                timeout=30,
            )
            print(f"Rendered provenance footer into {design_target}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not render provenance: {e}", file=sys.stderr)
    else:
        # Just copy without provenance
        design_target.write_text(design_content, encoding="utf-8")
        print(f"Warning: Provenance script not found, copied design without footer", file=sys.stderr)

    print(f"Updated design at: {design_target}")

    # Stage the file
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "add", str(design_target)],
            check=True,
            timeout=30,
        )
        print(f"Staged: {design_target}")
    except subprocess.CalledProcessError as e:
        print(f"Error staging file: {e}", file=sys.stderr)
        return 1

    # Commit
    commit_message = f"{jira_key}: Address design review feedback\n\nAssisted-by: Claude Code <noreply@anthropic.com>"
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "commit", "-m", commit_message],
            check=True,
            timeout=30,
        )
        print(f"Committed design updates")
    except subprocess.CalledProcessError as e:
        # Check if it's because there's nothing to commit
        status_result = subprocess.run(
            ["git", "-C", str(docs_repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if not status_result.stdout.strip():
            print("No changes to commit (file already up to date)")
        else:
            print(f"Error committing: {e}", file=sys.stderr)
            return 1

    # Push to fork
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "push", "fork", branch_name],
            check=True,
            timeout=60,
        )
        print(f"Pushed updates to fork/{branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to fork: {e}", file=sys.stderr)
        return 1

    pr_url = metadata.get("pr_url")
    if pr_url:
        print(f"\nPR updated: {pr_url}")
    else:
        print("\nChanges pushed to branch")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply design reviewer feedback and update the PR"
    )
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")

    args = parser.parse_args()

    return respond_design(args.jira_key, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
