#!/usr/bin/env python3
"""Fetch a Jira feature and format it for PRD generation."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def run_jira_command(args: list[str]) -> str:
    """Run a jira CLI command and return output."""
    try:
        result = subprocess.run(
            ["jira"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running jira command: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: jira CLI not found. Install it first.", file=sys.stderr)
        sys.exit(1)


def fetch_issue(issue_key: str) -> Dict[str, Any]:
    """Fetch issue details using jira CLI."""
    output = run_jira_command(["issue", "view", issue_key, "--plain"])
    lines = output.strip().split("\n")

    issue_data = {
        "key": issue_key,
        "summary": "",
        "description": "",
        "status": "",
        "priority": "",
        "labels": [],
        "acceptance_criteria": "",
        "comments": [],
        "links": []
    }

    current_section = None
    section_lines = []

    for line in lines:
        line = line.rstrip()

        if line.startswith("Summary:"):
            issue_data["summary"] = line.replace("Summary:", "").strip()
        elif line.startswith("Status:"):
            issue_data["status"] = line.replace("Status:", "").strip()
        elif line.startswith("Priority:"):
            issue_data["priority"] = line.replace("Priority:", "").strip()
        elif line.startswith("Labels:"):
            labels_str = line.replace("Labels:", "").strip()
            if labels_str:
                issue_data["labels"] = [l.strip() for l in labels_str.split(",")]
        elif line.startswith("Description:"):
            current_section = "description"
            section_lines = []
        elif line.startswith("Acceptance Criteria:") or line.startswith("Definition of Done:"):
            if current_section == "description":
                issue_data["description"] = "\n".join(section_lines).strip()
            current_section = "acceptance_criteria"
            section_lines = []
        elif line.startswith("Comments:"):
            if current_section == "description":
                issue_data["description"] = "\n".join(section_lines).strip()
            elif current_section == "acceptance_criteria":
                issue_data["acceptance_criteria"] = "\n".join(section_lines).strip()
            current_section = "comments"
            section_lines = []
        elif line.startswith("Links:"):
            if current_section == "description":
                issue_data["description"] = "\n".join(section_lines).strip()
            elif current_section == "acceptance_criteria":
                issue_data["acceptance_criteria"] = "\n".join(section_lines).strip()
            elif current_section == "comments":
                parse_comments(section_lines, issue_data)
            current_section = "links"
            section_lines = []
        elif current_section:
            section_lines.append(line)

    if current_section == "description":
        issue_data["description"] = "\n".join(section_lines).strip()
    elif current_section == "acceptance_criteria":
        issue_data["acceptance_criteria"] = "\n".join(section_lines).strip()
    elif current_section == "comments":
        parse_comments(section_lines, issue_data)
    elif current_section == "links":
        parse_links(section_lines, issue_data)

    return issue_data


def parse_comments(lines: list[str], issue_data: Dict[str, Any]):
    """Parse comments section from jira output."""
    current_comment = []

    for line in lines:
        if line.startswith("  - ") or line.startswith("  * "):
            if current_comment:
                comment_text = "\n".join(current_comment).strip()
                if is_substantive_comment(comment_text):
                    issue_data["comments"].append(comment_text)
            current_comment = [line[4:]]
        elif current_comment:
            current_comment.append(line.strip())

    if current_comment:
        comment_text = "\n".join(current_comment).strip()
        if is_substantive_comment(comment_text):
            issue_data["comments"].append(comment_text)


def is_substantive_comment(comment: str) -> bool:
    """Check if a comment is substantive (not just status updates)."""
    comment_lower = comment.lower()

    non_substantive_patterns = [
        "status changed",
        "moved to",
        "assigned to",
        "unassigned",
        "priority changed",
        "started work",
        "stopped work",
        "logged time",
    ]

    for pattern in non_substantive_patterns:
        if pattern in comment_lower:
            return False

    return len(comment.strip()) > 20


def parse_links(lines: list[str], issue_data: Dict[str, Any]):
    """Parse links section from jira output."""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("*"):
            continue

        if "relates to" in line.lower() or "is related to" in line.lower():
            parts = line.split()
            for part in parts:
                if part.startswith("OSAC-") or part.startswith("NVIDIA-") or part.startswith("RHEL-"):
                    issue_data["links"].append(part.strip())


def fetch_linked_issues(issue_key: str, links: list[str]) -> Dict[str, Dict[str, str]]:
    """Fetch linked issues (one level only)."""
    linked_issues = {}

    for link_key in links:
        if link_key == issue_key:
            continue

        try:
            output = run_jira_command(["issue", "view", link_key, "--plain"])
            lines = output.strip().split("\n")

            linked_issue = {
                "key": link_key,
                "summary": "",
                "status": "",
            }

            for line in lines:
                if line.startswith("Summary:"):
                    linked_issue["summary"] = line.replace("Summary:", "").strip()
                elif line.startswith("Status:"):
                    linked_issue["status"] = line.replace("Status:", "").strip()

            if linked_issue["summary"]:
                linked_issues[link_key] = linked_issue

        except Exception as e:
            print(f"Warning: Could not fetch linked issue {link_key}: {e}", file=sys.stderr)

    return linked_issues


def format_as_markdown(issue_data: Dict[str, Any], linked_issues: Dict[str, Dict[str, str]]) -> str:
    """Format issue data as markdown."""
    md_lines = [
        f"# {issue_data['key']}: {issue_data['summary']}",
        "",
        "## Metadata",
        "",
        f"- **Status**: {issue_data['status']}",
        f"- **Priority**: {issue_data['priority']}",
    ]

    if issue_data['labels']:
        md_lines.append(f"- **Labels**: {', '.join(issue_data['labels'])}")

    md_lines.extend([
        "",
        "## Description",
        "",
        issue_data['description'] if issue_data['description'] else "(No description)",
        "",
    ])

    if issue_data['acceptance_criteria']:
        md_lines.extend([
            "## Acceptance Criteria",
            "",
            issue_data['acceptance_criteria'],
            "",
        ])

    if issue_data['comments']:
        md_lines.extend([
            "## Comments",
            "",
        ])
        for i, comment in enumerate(issue_data['comments'], 1):
            md_lines.extend([
                f"### Comment {i}",
                "",
                comment,
                "",
            ])

    if linked_issues:
        md_lines.extend([
            "## Linked Issues",
            "",
        ])
        for link_key, link_data in linked_issues.items():
            md_lines.append(f"- **{link_key}** ({link_data['status']}): {link_data['summary']}")
        md_lines.append("")

    return "\n".join(md_lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch a Jira feature and format it for PRD generation")
    parser.add_argument("issue_key", help="Jira issue key (e.g., OSAC-1269)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    args = parser.parse_args()

    print(f"Fetching {args.issue_key}...", file=sys.stderr)
    issue_data = fetch_issue(args.issue_key)

    print(f"Fetching {len(issue_data['links'])} linked issues...", file=sys.stderr)
    linked_issues = fetch_linked_issues(args.issue_key, issue_data['links'])

    markdown = format_as_markdown(issue_data, linked_issues)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown)
        print(f"Wrote source to {args.output}", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
