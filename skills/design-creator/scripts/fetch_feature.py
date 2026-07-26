#!/usr/bin/env python3
"""Fetch a Jira feature and format it for PRD generation.

Parses the `jira issue view KEY --plain` output format which uses:
- Emoji-prefixed metadata on the first line (type, status, date, assignee, key)
- `# Title` on a separate line
- Metadata line with created date, reporter, priority, components, labels
- `--- Description ---` section separator
- `--- Linked Issues ---` section separator (if present)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_jira_command(args: list) -> str:
    try:
        result = subprocess.run(
            ["jira"] + args,
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running jira command: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: jira CLI not found.", file=sys.stderr)
        sys.exit(1)


def parse_jira_output(output: str, issue_key: str) -> dict:
    """Parse `jira issue view --plain` output into structured data."""
    lines = output.split("\n")
    data = {
        "key": issue_key,
        "summary": "",
        "description": "",
        "status": "",
        "priority": "",
        "labels": [],
        "components": [],
        "assignee": "",
        "reporter": "",
        "links": [],
    }

    SECTION_SEP = re.compile(r"^-{10,}\s+(.+?)\s+-{10,}$")

    header_line = ""
    meta_line = ""
    current_section = None
    section_content = []
    sections = {}

    for line in lines:
        stripped = line.strip()

        sep_match = SECTION_SEP.match(stripped)
        if sep_match:
            if current_section:
                sections[current_section] = "\n".join(section_content).strip()
            current_section = sep_match.group(1).strip()
            section_content = []
            continue

        if stripped.startswith("# ") and not data["summary"]:
            data["summary"] = stripped[2:].strip()
            continue

        if "🔑" in stripped and not header_line:
            header_line = stripped
            continue

        if ("🔎" in stripped or "🚀" in stripped) and not meta_line:
            meta_line = stripped
            continue

        if current_section:
            section_content.append(line.rstrip())

    if current_section:
        sections[current_section] = "\n".join(section_content).strip()

    if header_line:
        if "🚧" in header_line:
            data["status"] = "In Progress"
        elif "✅" in header_line:
            data["status"] = "Done"
        elif "📋" in header_line or "To Do" in header_line:
            data["status"] = "To Do"
        else:
            status_match = re.search(r"[⭐🚧✅📋🔴]\s*(\S+(?:\s+\S+)?)", header_line)
            if status_match:
                data["status"] = status_match.group(1).strip()

        assignee_match = re.search(r"👷\s*(.+?)(?:\s+🔑|$)", header_line)
        if assignee_match:
            data["assignee"] = assignee_match.group(1).strip()

    if meta_line:
        reporter_match = re.search(r"🔎\s*(.+?)(?:\s+🚀|$)", meta_line)
        if reporter_match:
            data["reporter"] = reporter_match.group(1).strip()

        priority_match = re.search(r"🚀\s*(.+?)(?:\s+📦|$)", meta_line)
        if priority_match:
            data["priority"] = priority_match.group(1).strip()

        component_match = re.search(r"📦\s*(.+?)(?:\s+🏷|$)", meta_line)
        if component_match:
            data["components"] = [c.strip() for c in component_match.group(1).split(",") if c.strip()]

        label_match = re.search(r"🏷️?\s*(.+?)(?:\s+👀|$)", meta_line)
        if label_match:
            data["labels"] = [l.strip() for l in label_match.group(1).split(",") if l.strip()]

    data["description"] = sections.get("Description", "")

    linked_text = sections.get("Linked Issues", "")
    if linked_text:
        for match in re.finditer(r"(OSAC-\d+)", linked_text):
            link_key = match.group(1)
            if link_key != issue_key:
                data["links"].append(link_key)
        data["links"] = list(set(data["links"]))

    return data


def fetch_linked_issues(issue_key: str, links: list) -> dict:
    linked = {}
    for link_key in links[:5]:
        if link_key == issue_key:
            continue
        try:
            output = run_jira_command(["issue", "view", link_key, "--plain"])
            link_data = parse_jira_output(output, link_key)
            if link_data["summary"]:
                linked[link_key] = {
                    "key": link_key,
                    "summary": link_data["summary"],
                    "status": link_data["status"],
                }
        except Exception as e:
            print(f"Warning: Could not fetch {link_key}: {e}", file=sys.stderr)
    return linked


def validate_source(content: str) -> bool:
    desc_lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("-")]
    if len(desc_lines) < 5:
        return False
    if "(No description)" in content:
        return False
    return True


def format_as_markdown(data: dict, linked: dict) -> str:
    lines = [
        f"# {data['key']}: {data['summary']}",
        "",
        "## Metadata",
        "",
        f"- **Status**: {data['status']}",
        f"- **Priority**: {data['priority']}",
        f"- **Assignee**: {data['assignee']}",
        f"- **Reporter**: {data['reporter']}",
    ]
    if data["components"]:
        lines.append(f"- **Components**: {', '.join(data['components'])}")
    if data["labels"]:
        lines.append(f"- **Labels**: {', '.join(data['labels'])}")

    lines.extend(["", "## Description", ""])
    if data["description"]:
        lines.append(data["description"])
    else:
        lines.append("(No description)")
    lines.append("")

    if linked:
        lines.extend(["## Linked Issues", ""])
        for lk, ld in linked.items():
            lines.append(f"- **{lk}** ({ld['status']}): {ld['summary']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch a Jira feature for PRD generation")
    parser.add_argument("issue_key", help="Jira issue key (e.g., OSAC-1269)")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    print(f"Fetching {args.issue_key}...", file=sys.stderr)
    output = run_jira_command(["issue", "view", args.issue_key, "--plain"])
    data = parse_jira_output(output, args.issue_key)

    print(f"Fetching {len(data['links'])} linked issues...", file=sys.stderr)
    linked = fetch_linked_issues(args.issue_key, data["links"])

    markdown = format_as_markdown(data, linked)

    if not validate_source(markdown):
        print(f"WARNING: Source has minimal content. Jira parsing may have failed.", file=sys.stderr)

    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(markdown)
        print(f"Wrote source to {args.output}", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
