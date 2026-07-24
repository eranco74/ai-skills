#!/usr/bin/env python3
"""State persistence utility for PRD generation workflows."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


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


def init_state(path: str, updates: Dict[str, str]):
    """Create a new state file with initial values."""
    file_path = Path(path)

    if file_path.exists():
        print(f"Error: File already exists: {path}", file=sys.stderr)
        sys.exit(1)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    state = {}
    for key, value_str in updates.items():
        state[key] = parse_value(value_str)

    with file_path.open("w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

    print(f"Initialized state file: {path}")


def set_state(path: str, updates: Dict[str, str]):
    """Update values in an existing state file."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with file_path.open("r") as f:
        state = json.load(f)

    for key, value_str in updates.items():
        state[key] = parse_value(value_str)

    with file_path.open("w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

    print(f"Updated state file: {path}")


def set_default_state(path: str, updates: Dict[str, str]):
    """Set values in state file only if keys are absent."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with file_path.open("r") as f:
        state = json.load(f)

    changed = False
    for key, value_str in updates.items():
        if key not in state:
            state[key] = parse_value(value_str)
            changed = True

    if changed:
        with file_path.open("w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
        print(f"Updated state file with defaults: {path}")
    else:
        print(f"No defaults needed: {path}")


def read_state(path: str):
    """Read and print state file contents."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with file_path.open("r") as f:
        state = json.load(f)

    print(json.dumps(state, indent=2))


def write_ids(path: str, ids: list[str]):
    """Write a list of IDs to a file."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w") as f:
        for id_str in ids:
            f.write(id_str + "\n")

    print(f"Wrote {len(ids)} IDs to {path}")


def read_ids(path: str):
    """Read IDs from file and print space-separated."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with file_path.open("r") as f:
        ids = [line.strip() for line in f if line.strip()]

    print(" ".join(ids))


def print_timestamp():
    """Print current UTC timestamp in ISO 8601 format."""
    now = datetime.now(timezone.utc)
    print(now.isoformat())


def clean_tmp():
    """Reset tmp/ directory."""
    tmp_dir = Path("tmp")

    if tmp_dir.exists():
        for item in tmp_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                for subitem in item.rglob("*"):
                    if subitem.is_file():
                        subitem.unlink()
                for subitem in sorted(item.rglob("*"), reverse=True):
                    if subitem.is_dir():
                        subitem.rmdir()
                item.rmdir()

    tmp_dir.mkdir(exist_ok=True)
    print("Cleaned tmp/ directory")


def main():
    parser = argparse.ArgumentParser(description="State persistence utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create config file")
    init_parser.add_argument("file", help="Path to state file")
    init_parser.add_argument("updates", nargs="*", help="Initial values in key=value format")

    set_parser = subparsers.add_parser("set", help="Update keys in state file")
    set_parser.add_argument("file", help="Path to state file")
    set_parser.add_argument("updates", nargs="+", help="Updates in key=value format")

    set_default_parser = subparsers.add_parser("set-default", help="Set only if key absent")
    set_default_parser.add_argument("file", help="Path to state file")
    set_default_parser.add_argument("updates", nargs="+", help="Defaults in key=value format")

    read_parser = subparsers.add_parser("read", help="Print file contents")
    read_parser.add_argument("file", help="Path to state file")

    write_ids_parser = subparsers.add_parser("write-ids", help="Write ID list to file")
    write_ids_parser.add_argument("file", help="Path to ID list file")
    write_ids_parser.add_argument("ids", nargs="*", help="IDs to write")

    read_ids_parser = subparsers.add_parser("read-ids", help="Print IDs space-separated")
    read_ids_parser.add_argument("file", help="Path to ID list file")

    subparsers.add_parser("timestamp", help="Print current UTC ISO 8601 time")

    subparsers.add_parser("clean", help="Reset tmp/ directory")

    args = parser.parse_args()

    if args.command == "init":
        updates = {}
        for update in args.updates:
            if "=" not in update:
                print(f"Error: Invalid format '{update}', expected key=value", file=sys.stderr)
                sys.exit(1)
            key, value = update.split("=", 1)
            updates[key] = value
        init_state(args.file, updates)

    elif args.command == "set":
        updates = {}
        for update in args.updates:
            if "=" not in update:
                print(f"Error: Invalid format '{update}', expected key=value", file=sys.stderr)
                sys.exit(1)
            key, value = update.split("=", 1)
            updates[key] = value
        set_state(args.file, updates)

    elif args.command == "set-default":
        updates = {}
        for update in args.updates:
            if "=" not in update:
                print(f"Error: Invalid format '{update}', expected key=value", file=sys.stderr)
                sys.exit(1)
            key, value = update.split("=", 1)
            updates[key] = value
        set_default_state(args.file, updates)

    elif args.command == "read":
        read_state(args.file)

    elif args.command == "write-ids":
        write_ids(args.file, args.ids)

    elif args.command == "read-ids":
        read_ids(args.file)

    elif args.command == "timestamp":
        print_timestamp()

    elif args.command == "clean":
        clean_tmp()


if __name__ == "__main__":
    main()
