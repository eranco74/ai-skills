#!/usr/bin/env python3
"""Publish PRD to enhancement-proposals repo as a GitHub PR.

Usage:
    python3 scripts/publish_prd.py {JIRA_KEY} [--dry-run]

Fully autonomous: creates branch, commits, pushes to fork, opens draft PR.
"""

import argparse
import json
import re
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


def slugify(text: str) -> str:
    """Convert title to URL-friendly slug."""
    # Lowercase and replace spaces/underscores with hyphens
    slug = text.lower().replace(" ", "-").replace("_", "-")
    # Remove special characters except hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    return slug.strip("-")


def extract_title_from_source(source_file: Path) -> str | None:
    """Extract title from Jira source file (first heading)."""
    if not source_file.is_file():
        return None
    content = source_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return None


def run_git(repo_path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run git command in the given repo."""
    return subprocess.run(
        ["git", "-C", str(repo_path)] + list(args),
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def publish_prd(jira_key: str, dry_run: bool = False) -> int:
    """Publish PRD to enhancement-proposals repo."""
    root = workspace_root()
    artifacts_dir = root / ".artifacts" / "prd" / jira_key
    prd_file = artifacts_dir / "03-prd.md"
    config_file = root / ".artifacts" / "prd" / "config.json"

    # Verify PRD exists
    if not prd_file.is_file():
        print(f"Error: PRD file not found: {prd_file}", file=sys.stderr)
        return 1

    # Read config
    if not config_file.is_file():
        print(f"Error: config.json not found: {config_file}", file=sys.stderr)
        print("Run bridge_artifacts.py first", file=sys.stderr)
        return 1

    config = json.loads(config_file.read_text(encoding="utf-8"))
    docs_repo_path = Path(config["docs_repo_path"])

    if not docs_repo_path.is_dir():
        print(f"Error: docs repo not found: {docs_repo_path}", file=sys.stderr)
        return 1

    # Fetch origin
    print(f"Fetching origin in {docs_repo_path}...")
    try:
        run_git(docs_repo_path, "fetch", "origin")
    except subprocess.CalledProcessError as exc:
        print(f"Error: git fetch failed: {exc.stderr}", file=sys.stderr)
        return 1

    # Derive slug from title
    source_file = root / "artifacts" / "prd-tasks" / f"{jira_key}-source.md"
    title = extract_title_from_source(source_file)
    if not title:
        print(f"Warning: Could not extract title from {source_file}", file=sys.stderr)
        title = f"feature-{jira_key.lower()}"
    slug = slugify(title)
    print(f"Derived slug: {slug}")

    # Feature directory and branch
    feature_dir = docs_repo_path / "enhancements" / f"{jira_key}-{slug}"
    branch_name = f"prd/{jira_key}"

    # Create or checkout branch from origin/main
    current_branch_result = run_git(docs_repo_path, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else None

    branch_exists = run_git(docs_repo_path, "rev-parse", "--verify", branch_name, check=False).returncode == 0

    if branch_exists:
        print(f"Branch {branch_name} exists, checking out...")
        try:
            run_git(docs_repo_path, "checkout", branch_name)
        except subprocess.CalledProcessError as exc:
            print(f"Error: git checkout failed: {exc.stderr}", file=sys.stderr)
            return 1
    else:
        print(f"Creating branch {branch_name} from origin/main...")
        try:
            run_git(docs_repo_path, "checkout", "-b", branch_name, "origin/main")
        except subprocess.CalledProcessError as exc:
            print(f"Error: git checkout -b failed: {exc.stderr}", file=sys.stderr)
            return 1

    # Create feature directory
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Copy PRD
    target_prd = feature_dir / "prd.md"
    shutil.copy2(prd_file, target_prd)
    print(f"Copied PRD to {target_prd}")

    # Render provenance footer
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if provenance_script.is_file():
        try:
            subprocess.run(
                [
                    "python3",
                    str(provenance_script),
                    "render",
                    "--workflow", "prd",
                    "--issue", jira_key,
                    "--target", str(target_prd),
                ],
                check=True,
                timeout=30,
            )
            print(f"Rendered provenance footer in {target_prd}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"Warning: provenance render failed: {exc}", file=sys.stderr)
    else:
        print(f"Warning: provenance script not found: {provenance_script}", file=sys.stderr)

    # Stage file
    try:
        run_git(docs_repo_path, "add", str(target_prd.relative_to(docs_repo_path)))
    except subprocess.CalledProcessError as exc:
        print(f"Error: git add failed: {exc.stderr}", file=sys.stderr)
        return 1

    # Check if there are changes to commit
    diff_result = run_git(docs_repo_path, "diff", "--staged", "--quiet", check=False)
    if diff_result.returncode == 0:
        print("No changes to commit")
    else:
        # Commit with sign-off and AI attribution
        commit_message = f"""PRD {jira_key}: {title}

Assisted-by: Claude Code <noreply@anthropic.com>
"""
        try:
            run_git(docs_repo_path, "commit", "-s", "-m", commit_message)
            print("Committed changes")
        except subprocess.CalledProcessError as exc:
            print(f"Error: git commit failed: {exc.stderr}", file=sys.stderr)
            return 1

    if dry_run:
        print("Dry run: skipping push and PR creation")
        # Restore original branch
        if current_branch and current_branch != branch_name:
            run_git(docs_repo_path, "checkout", current_branch, check=False)
        return 0

    # Push to fork
    print(f"Pushing {branch_name} to fork...")
    try:
        run_git(docs_repo_path, "push", "fork", branch_name, "-u")
    except subprocess.CalledProcessError as exc:
        print(f"Error: git push failed: {exc.stderr}", file=sys.stderr)
        return 1

    # Create draft PR
    pr_title = f"{jira_key}: {title}"
    pr_body = f"""## Summary

PRD for {jira_key}.

## Review Checklist

- [ ] Problem statement is user-focused
- [ ] All affected personas have user stories
- [ ] Scope boundaries are clear
- [ ] No design leakage

🤖 Generated with prd-creator
"""

    try:
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", "osac-project/enhancement-proposals",
                "--base", "main",
                "--head", f"fork:{branch_name}",
                "--title", pr_title,
                "--body", pr_body,
                "--draft",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=docs_repo_path,
        )
        pr_url = result.stdout.strip()
        print(f"Created draft PR: {pr_url}")

        # Extract PR number from URL
        pr_number_match = re.search(r"/pull/(\d+)", pr_url)
        pr_number = int(pr_number_match.group(1)) if pr_number_match else None

    except subprocess.CalledProcessError as exc:
        # Check if PR already exists
        if "already exists" in exc.stderr:
            print("PR already exists, fetching URL...")
            try:
                list_result = subprocess.run(
                    [
                        "gh", "pr", "list",
                        "--repo", "osac-project/enhancement-proposals",
                        "--head", f"fork:{branch_name}",
                        "--json", "number,url",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=docs_repo_path,
                )
                prs = json.loads(list_result.stdout)
                if prs:
                    pr_url = prs[0]["url"]
                    pr_number = prs[0]["number"]
                    print(f"Found existing PR: {pr_url}")
                else:
                    print("Error: PR exists but could not be found", file=sys.stderr)
                    return 1
            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as list_exc:
                print(f"Error: could not list PRs: {list_exc}", file=sys.stderr)
                return 1
        else:
            print(f"Error: gh pr create failed: {exc.stderr}", file=sys.stderr)
            return 1

    # Save publish metadata
    publish_metadata = {
        "jira_key": jira_key,
        "pr_number": pr_number,
        "pr_url": pr_url if 'pr_url' in locals() else None,
        "branch": branch_name,
        "feature_dir": str(feature_dir.relative_to(docs_repo_path)),
    }
    metadata_file = artifacts_dir / "publish-metadata.json"
    metadata_file.write_text(json.dumps(publish_metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved publish metadata: {metadata_file}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish PRD to enhancement-proposals")
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument("--dry-run", action="store_true", help="Skip push and PR creation")
    args = parser.parse_args()

    try:
        return publish_prd(args.jira_key, args.dry_run)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
