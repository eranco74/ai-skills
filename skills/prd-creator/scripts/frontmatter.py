#!/usr/bin/env python3
"""YAML frontmatter management utility for PRD files."""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


PRD_TASK_SCHEMA = {
    "prd_id": {"type": str, "required": True},
    "title": {"type": str, "required": True},
    "jira_key": {"type": str, "required": True},
    "author": {"type": str, "required": False},
    "status": {"type": str, "required": False, "enum": ["Draft", "Ready", "Submitted", "Archived"]},
    "score": {"type": int, "required": False, "nullable": True, "min": 0, "max": 10},
    "pass": {"type": bool, "required": False, "nullable": True},
}

PRD_REVIEW_SCHEMA = {
    "prd_id": {"type": str, "required": True},
    "score": {"type": int, "required": True, "min": 0, "max": 10},
    "pass": {"type": bool, "required": True},
    "recommendation": {"type": str, "required": True, "enum": ["submit", "revise", "reject"]},
    "auto_revised": {"type": bool, "required": False, "default": False},
    "needs_attention": {"type": bool, "required": False, "default": False},
    "needs_attention_reason": {"type": str, "required": False, "nullable": True},
    "scores.what": {"type": int, "required": False, "min": 0, "max": 2},
    "scores.why": {"type": int, "required": False, "min": 0, "max": 2},
    "scores.user_facing": {"type": int, "required": False, "min": 0, "max": 2},
    "scores.right_sized": {"type": int, "required": False, "min": 0, "max": 2},
    "scores.testability": {"type": int, "required": False, "min": 0, "max": 2},
    "before_score": {"type": int, "required": False, "nullable": True, "min": 0, "max": 10},
    "before_scores.what": {"type": int, "required": False, "nullable": True, "min": 0, "max": 2},
    "before_scores.why": {"type": int, "required": False, "nullable": True, "min": 0, "max": 2},
    "before_scores.user_facing": {"type": int, "required": False, "nullable": True, "min": 0, "max": 2},
    "before_scores.right_sized": {"type": int, "required": False, "nullable": True, "min": 0, "max": 2},
    "before_scores.testability": {"type": int, "required": False, "nullable": True, "min": 0, "max": 2},
}


def print_schema(schema_type: str):
    """Print schema for PRD task or review files."""
    if schema_type == "prd-task":
        schema = PRD_TASK_SCHEMA
    elif schema_type == "prd-review":
        schema = PRD_REVIEW_SCHEMA
    else:
        print(f"Error: Unknown schema type '{schema_type}'", file=sys.stderr)
        sys.exit(1)

    print(yaml.dump(schema, default_flow_style=False, sort_keys=False))


def parse_frontmatter(content: str) -> tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None, content

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, content

    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]
        return frontmatter, body
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML frontmatter: {e}", file=sys.stderr)
        sys.exit(1)


def set_nested_value(data: Dict[str, Any], key: str, value: Any):
    """Set a nested dictionary value using dot notation."""
    parts = key.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value


def get_nested_value(data: Dict[str, Any], key: str) -> Any:
    """Get a nested dictionary value using dot notation."""
    parts = key.split(".")
    current = data

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]

    return current


def parse_value(value_str: str) -> Any:
    """Parse a string value to appropriate type."""
    value_str = value_str.strip()

    if value_str.lower() == "true":
        return True
    elif value_str.lower() == "false":
        return False
    elif value_str.lower() == "null" or value_str.lower() == "none":
        return None

    try:
        return int(value_str)
    except ValueError:
        pass

    try:
        return float(value_str)
    except ValueError:
        pass

    return value_str


def validate_frontmatter(frontmatter: Dict[str, Any], schema: Dict[str, Any]) -> list[str]:
    """Validate frontmatter against schema."""
    errors = []

    for field, rules in schema.items():
        value = get_nested_value(frontmatter, field)

        if rules.get("required", False) and value is None:
            errors.append(f"Missing required field: {field}")
            continue

        if value is None:
            if not rules.get("nullable", False) and not rules.get("required", False):
                continue
            if rules.get("nullable", True):
                continue

        expected_type = rules["type"]
        if not isinstance(value, expected_type):
            errors.append(f"Field '{field}' must be of type {expected_type.__name__}, got {type(value).__name__}")
            continue

        if "enum" in rules and value not in rules["enum"]:
            errors.append(f"Field '{field}' must be one of {rules['enum']}, got '{value}'")

        if "min" in rules and isinstance(value, int) and value < rules["min"]:
            errors.append(f"Field '{field}' must be >= {rules['min']}, got {value}")

        if "max" in rules and isinstance(value, int) and value > rules["max"]:
            errors.append(f"Field '{field}' must be <= {rules['max']}, got {value}")

    return errors


def set_frontmatter(path: str, updates: Dict[str, str]):
    """Set or update frontmatter fields on a file."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        frontmatter = {}

    for key, value_str in updates.items():
        value = parse_value(value_str)
        set_nested_value(frontmatter, key, value)

    new_content = "---\n" + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + "---\n" + body
    file_path.write_text(new_content)
    print(f"Updated frontmatter in {path}")


def read_frontmatter(path: str):
    """Read and print validated frontmatter as JSON."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text()
    frontmatter, _ = parse_frontmatter(content)

    if frontmatter is None:
        print("{}")
    else:
        print(json.dumps(frontmatter, indent=2))


def rebuild_index():
    """Rebuild artifacts/prds.md index from all frontmatter in artifacts/prd-tasks/."""
    tasks_dir = Path("artifacts/prd-tasks")

    if not tasks_dir.exists():
        print("Error: artifacts/prd-tasks/ directory not found", file=sys.stderr)
        sys.exit(1)

    prds = []

    for md_file in sorted(tasks_dir.glob("*.md")):
        if md_file.name.endswith("-source.md") or md_file.name.endswith("-review.md"):
            continue

        content = md_file.read_text()
        frontmatter, _ = parse_frontmatter(content)

        if frontmatter and "prd_id" in frontmatter:
            prds.append({
                "file": md_file.name,
                "prd_id": frontmatter.get("prd_id"),
                "title": frontmatter.get("title", ""),
                "status": frontmatter.get("status", "Draft"),
                "score": frontmatter.get("score"),
                "pass": frontmatter.get("pass"),
            })

    index_path = Path("artifacts/prds.md")

    with index_path.open("w") as f:
        f.write("# PRD Index\n\n")
        f.write("| PRD ID | Title | Status | Score | Pass | File |\n")
        f.write("|--------|-------|--------|-------|------|------|\n")

        for prd in prds:
            score_str = str(prd["score"]) if prd["score"] is not None else "-"
            pass_str = "✓" if prd["pass"] is True else "✗" if prd["pass"] is False else "-"
            f.write(f"| {prd['prd_id']} | {prd['title']} | {prd['status']} | {score_str} | {pass_str} | [{prd['file']}](prd-tasks/{prd['file']}) |\n")

    print(f"Rebuilt index with {len(prds)} PRDs at {index_path}")


def main():
    parser = argparse.ArgumentParser(description="YAML frontmatter management utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    schema_parser = subparsers.add_parser("schema", help="Print schema for PRD task or review files")
    schema_parser.add_argument("type", choices=["prd-task", "prd-review"])

    set_parser = subparsers.add_parser("set", help="Set/update frontmatter on a file")
    set_parser.add_argument("path", help="Path to markdown file")
    set_parser.add_argument("updates", nargs="+", help="Field updates in key=value format")

    read_parser = subparsers.add_parser("read", help="Read and print validated frontmatter as JSON")
    read_parser.add_argument("path", help="Path to markdown file")

    subparsers.add_parser("rebuild-index", help="Rebuild artifacts/prds.md index")

    args = parser.parse_args()

    if args.command == "schema":
        print_schema(args.type)
    elif args.command == "set":
        updates = {}
        for update in args.updates:
            if "=" not in update:
                print(f"Error: Invalid update format '{update}', expected key=value", file=sys.stderr)
                sys.exit(1)
            key, value = update.split("=", 1)
            updates[key] = value
        set_frontmatter(args.path, updates)
    elif args.command == "read":
        read_frontmatter(args.path)
    elif args.command == "rebuild-index":
        rebuild_index()


if __name__ == "__main__":
    main()
