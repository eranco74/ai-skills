#!/usr/bin/env python3
"""Handle PR reviewer comments for published PRDs.

Usage:
    python3 scripts/respond_prd.py {JIRA_KEY} [--dry-run]

Fetches PR comments, writes summary, waits for revision, then pushes update and posts replies.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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


def run_git(repo_path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run git command in the given repo."""
    return subprocess.run(
        ["git", "-C", str(repo_path)] + list(args),
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def fetch_pr_comments(repo: str, pr_number: int) -> dict:
    """Fetch PR comments using gh CLI."""
    try:
        # Fetch PR view with comments and reviews
        result = subprocess.run(
            [
                "gh", "pr", "view", str(pr_number),
                "--repo", repo,
                "--json", "comments,reviews",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        pr_data = json.loads(result.stdout)

        # Fetch review comments (line-level)
        api_result = subprocess.run(
            [
                "gh", "api",
                f"repos/{repo}/pulls/{pr_number}/comments",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        review_comments = json.loads(api_result.stdout)

        return {
            "comments": pr_data.get("comments", []),
            "reviews": pr_data.get("reviews", []),
            "review_comments": review_comments,
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Error fetching PR comments: {exc}", file=sys.stderr)
        return {"comments": [], "reviews": [], "review_comments": []}


def categorize_comment(text: str) -> str:
    """Categorize comment based on content."""
    text_lower = text.lower()
    if any(word in text_lower for word in ["approve", "lgtm", "looks good"]):
        return "approval"
    elif any(word in text_lower for word in ["clarify", "unclear", "what", "why", "how"]):
        return "clarification"
    elif any(word in text_lower for word in ["fix", "change", "update", "incorrect", "wrong"]):
        return "correction"
    elif any(word in text_lower for word in ["scope", "out of scope", "should include", "missing"]):
        return "scope_question"
    elif any(word in text_lower for word in ["requirement", "need", "must", "should"]):
        return "new_requirement"
    else:
        return "general"


def format_comment_summary(comments_data: dict) -> str:
    """Format comment summary for the revision agent."""
    lines = [
        "# PR Review Comments Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # Top-level comments
    if comments_data["comments"]:
        lines.append("## Top-Level Comments")
        lines.append("")
        for comment in comments_data["comments"]:
            author = comment.get("author", {}).get("login", "unknown")
            body = comment.get("body", "").strip()
            category = categorize_comment(body)
            lines.append(f"### [{category}] @{author}")
            lines.append("")
            lines.append(body)
            lines.append("")

    # Review comments (line-level)
    if comments_data["review_comments"]:
        lines.append("## Line-Level Comments")
        lines.append("")
        for comment in comments_data["review_comments"]:
            author = comment.get("user", {}).get("login", "unknown")
            body = comment.get("body", "").strip()
            path = comment.get("path", "")
            line = comment.get("original_line", comment.get("line", "?"))
            category = categorize_comment(body)
            lines.append(f"### [{category}] @{author} — {path}:{line}")
            lines.append("")
            lines.append(body)
            lines.append("")

    # Reviews (approve/request changes/comment)
    if comments_data["reviews"]:
        lines.append("## Reviews")
        lines.append("")
        for review in comments_data["reviews"]:
            author = review.get("author", {}).get("login", "unknown")
            state = review.get("state", "COMMENTED")
            body = review.get("body", "").strip()
            lines.append(f"### {state} — @{author}")
            if body:
                lines.append("")
                lines.append(body)
            lines.append("")

    return "\n".join(lines)


def respond_prd(jira_key: str, dry_run: bool = False) -> int:
    """Handle PR reviewer comments."""
    root = workspace_root()
    artifacts_dir = root / ".artifacts" / "prd" / jira_key
    metadata_file = artifacts_dir / "publish-metadata.json"
    prd_reviews_dir = root / "artifacts" / "prd-reviews"
    prd_reviews_dir.mkdir(parents=True, exist_ok=True)

    # Read publish metadata
    if not metadata_file.is_file():
        print(f"Error: publish metadata not found: {metadata_file}", file=sys.stderr)
        print("Run publish_prd.py first", file=sys.stderr)
        return 1

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    pr_number = metadata.get("pr_number")
    if not pr_number:
        print("Error: PR number not found in publish metadata", file=sys.stderr)
        return 1

    repo = "osac-project/enhancement-proposals"
    print(f"Fetching comments for PR #{pr_number}...")

    # Fetch comments
    comments_data = fetch_pr_comments(repo, pr_number)

    if not any([
        comments_data["comments"],
        comments_data["reviews"],
        comments_data["review_comments"],
    ]):
        print("No comments found on PR")
        return 0

    # Write comment summary
    summary_file = prd_reviews_dir / f"{jira_key}-pr-comments.md"
    summary_content = format_comment_summary(comments_data)
    summary_file.write_text(summary_content, encoding="utf-8")
    print(f"Wrote comment summary: {summary_file}")

    # Output summary for revision agent
    print("")
    print("=" * 80)
    print(summary_content)
    print("=" * 80)
    print("")
    print("Next steps:")
    print("1. Revision agent should read the comment summary and update the PRD")
    print("2. Re-run this script to capture provenance, push update, and post replies")
    print("")
    print("For now, returning — manual workflow continues with revision agent")

    # Note: In a full autonomous workflow, this would wait for the revision agent
    # to complete, then continue with the steps below. For the initial implementation,
    # we output the summary and return, letting the operator invoke the revision
    # agent and re-run this script.

    # Check if PRD has been revised (placeholder for future automation)
    revised_prd = root / "artifacts" / "prd-tasks" / f"{jira_key}.md"
    if not revised_prd.is_file():
        print("Waiting for PRD revision...", file=sys.stderr)
        return 0

    # Capture provenance for respond phase
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if provenance_script.is_file():
        try:
            subprocess.run(
                [
                    "python3",
                    str(provenance_script),
                    "capture",
                    "--workflow", "prd",
                    "--issue", jira_key,
                    "--phase", "respond",
                    "--authoring-mode", "skill",
                ],
                check=True,
                timeout=30,
            )
            print(f"Captured provenance: prd/{jira_key} phase=respond")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"Warning: provenance capture failed: {exc}", file=sys.stderr)

    # Copy updated PRD to artifacts and render provenance
    config_file = root / ".artifacts" / "prd" / "config.json"
    if not config_file.is_file():
        print(f"Error: config.json not found: {config_file}", file=sys.stderr)
        return 1

    config = json.loads(config_file.read_text(encoding="utf-8"))
    docs_repo_path = Path(config["docs_repo_path"])
    feature_dir = docs_repo_path / metadata["feature_dir"]
    target_prd = feature_dir / "prd.md"

    # Copy revised PRD
    shutil.copy2(revised_prd, artifacts_dir / "03-prd.md")
    shutil.copy2(revised_prd, target_prd)
    print(f"Copied revised PRD to {target_prd}")

    # Render provenance footer
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

    if dry_run:
        print("Dry run: skipping commit, push, and reply posting")
        return 0

    # Commit and push
    branch_name = metadata["branch"]
    try:
        run_git(docs_repo_path, "add", str(target_prd.relative_to(docs_repo_path)))
        commit_message = f"""PRD {jira_key}: address review feedback

Assisted-by: Claude Code <noreply@anthropic.com>
"""
        run_git(docs_repo_path, "commit", "-s", "-m", commit_message)
        run_git(docs_repo_path, "push", "fork", branch_name)
        print(f"Pushed updated PRD to fork/{branch_name}")
    except subprocess.CalledProcessError as exc:
        print(f"Error: git operations failed: {exc.stderr}", file=sys.stderr)
        return 1

    # Post reply comments (placeholder — full implementation would parse comments
    # and generate appropriate responses based on revision changes)
    print("")
    print("TODO: Post reply comments to PR (not yet implemented)")
    print("Manual step: comment on PR with revision summary")

    # Log response
    response_log = prd_reviews_dir / f"{jira_key}-responses.md"
    log_entry = f"""
## Response {datetime.now(timezone.utc).isoformat()}

Updated PRD based on review comments. See commit history for details.

"""
    if response_log.is_file():
        existing = response_log.read_text(encoding="utf-8")
        response_log.write_text(existing + log_entry, encoding="utf-8")
    else:
        response_log.write_text(f"# PR Response Log — {jira_key}\n" + log_entry, encoding="utf-8")
    print(f"Updated response log: {response_log}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Handle PR reviewer comments")
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument("--dry-run", action="store_true", help="Skip push and reply posting")
    args = parser.parse_args()

    try:
        return respond_prd(args.jira_key, args.dry_run)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
