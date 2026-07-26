#!/usr/bin/env python3
"""Publish design to enhancement-proposals as a GitHub PR."""

import argparse
import json
import re
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


def slugify(text: str) -> str:
    """Convert text to lowercase hyphenated slug."""
    # Remove non-alphanumeric except hyphens and spaces
    text = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace whitespace and underscores with hyphens
    text = re.sub(r"[-\s]+", "-", text)
    # Remove leading/trailing hyphens
    return text.strip("-")


def get_jira_title(jira_key: str) -> str | None:
    """Get Jira issue title using jira CLI."""
    try:
        result = subprocess.run(
            ["jira", "issue", "view", jira_key, "--plain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Parse the output for the summary line
        for line in result.stdout.splitlines():
            if line.startswith("Summary:"):
                return line.split("Summary:", 1)[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def publish_design(jira_key: str, dry_run: bool = False) -> int:
    """Publish design to enhancement-proposals repo.

    Args:
        jira_key: The Jira issue key (e.g., OSAC-1234)
        dry_run: If True, print actions without executing

    Returns:
        0 on success, 1 on error
    """
    root = repo_root()

    # Read the design
    design_file = root / ".artifacts" / "design" / jira_key / "03-design.md"
    if not design_file.exists():
        print(f"Error: Design file not found: {design_file}", file=sys.stderr)
        print("Run bridge_artifacts.py first", file=sys.stderr)
        return 1

    design_content = design_file.read_text(encoding="utf-8")

    # Read docs repo config
    config_file = root / ".artifacts" / "prd" / "config.json"
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        print("Run bridge_artifacts.py with --docs-repo first", file=sys.stderr)
        return 1

    config = json.loads(config_file.read_text(encoding="utf-8"))
    docs_repo_path = Path(config["docs_repo_path"])

    if not docs_repo_path.exists():
        print(f"Error: Docs repo not found: {docs_repo_path}", file=sys.stderr)
        return 1

    # Try to inherit feature slug from PRD metadata
    feature_slug = None
    prd_metadata = root / ".artifacts" / "prd" / jira_key / "publish-metadata.json"
    if prd_metadata.exists():
        try:
            prd_meta = json.loads(prd_metadata.read_text(encoding="utf-8"))
            feature_slug = prd_meta.get("feature_slug")
            print(f"Inherited feature slug from PRD: {feature_slug}")
        except (json.JSONDecodeError, KeyError):
            pass

    # Derive slug from Jira if not inherited
    if not feature_slug:
        jira_title = get_jira_title(jira_key)
        if jira_title:
            feature_slug = slugify(jira_title)
            print(f"Derived feature slug from Jira: {feature_slug}")
        else:
            print(f"Warning: Could not get Jira title for {jira_key}", file=sys.stderr)
            feature_slug = "unknown-feature"

    # Feature directory: enhancements/{KEY}-{slug}/
    feature_dir_name = f"{jira_key}-{feature_slug}"
    feature_dir = docs_repo_path / "enhancements" / feature_dir_name
    design_target = feature_dir / "design.md"

    # Branch name
    branch_name = f"design/{jira_key}"

    print(f"\nPublish plan:")
    print(f"  Design file: {design_file}")
    print(f"  Target dir: {feature_dir}")
    print(f"  Target file: {design_target}")
    print(f"  Branch: {branch_name}")
    print(f"  Docs repo: {docs_repo_path}")

    if dry_run:
        print("\nDry run mode - no changes made")
        return 0

    # Create feature directory
    feature_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nCreated directory: {feature_dir}")

    # Check if branch exists
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "rev-parse", "--verify", branch_name],
            check=True,
            capture_output=True,
            timeout=30,
        )
        branch_exists = True
        print(f"Branch {branch_name} already exists, will switch to it")
    except subprocess.CalledProcessError:
        branch_exists = False

    # Create or switch to branch from origin/main
    try:
        if branch_exists:
            subprocess.run(
                ["git", "-C", str(docs_repo_path), "checkout", branch_name],
                check=True,
                timeout=30,
            )
        else:
            subprocess.run(
                ["git", "-C", str(docs_repo_path), "checkout", "-b", branch_name, "origin/main"],
                check=True,
                timeout=30,
            )
        print(f"Switched to branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating/switching branch: {e}", file=sys.stderr)
        return 1

    # Render provenance footer
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if provenance_script.exists():
        # First copy the design to target location so provenance can render into it
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

    print(f"Copied design to: {design_target}")

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
    commit_message = f"{jira_key}: Design for {feature_slug}\n\nAssisted-by: Claude Code <noreply@anthropic.com>"
    try:
        subprocess.run(
            ["git", "-C", str(docs_repo_path), "commit", "-m", commit_message],
            check=True,
            timeout=30,
        )
        print(f"Committed design")
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
            ["git", "-C", str(docs_repo_path), "push", "-u", "fork", branch_name],
            check=True,
            timeout=60,
        )
        print(f"Pushed to fork/{branch_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to fork: {e}", file=sys.stderr)
        return 1

    # Create draft PR
    pr_title = f"{jira_key}: Design for {feature_slug}"
    pr_body = f"Design document for {jira_key}.\n\nSee [Jira]({jira_key}) for requirements.\n\n🤖 Generated with Claude Code"

    try:
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", config["docs_repo_remote"].replace(".git", "").replace("https://github.com/", ""),
                "--head", f"fork:{branch_name}",
                "--base", "main",
                "--title", pr_title,
                "--body", pr_body,
                "--draft",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(docs_repo_path),
            timeout=60,
        )
        pr_url = result.stdout.strip()
        print(f"\nCreated draft PR: {pr_url}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating PR: {e}", file=sys.stderr)
        print("You may need to create the PR manually", file=sys.stderr)
        return 1

    # Save publish metadata
    metadata_file = root / ".artifacts" / "design" / jira_key / "publish-metadata.json"
    metadata = {
        "jira_key": jira_key,
        "feature_slug": feature_slug,
        "feature_dir": feature_dir_name,
        "branch_name": branch_name,
        "pr_url": pr_url if 'pr_url' in locals() else None,
    }
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved metadata: {metadata_file}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish design to enhancement-proposals as a GitHub PR"
    )
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")

    args = parser.parse_args()

    return publish_design(args.jira_key, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
