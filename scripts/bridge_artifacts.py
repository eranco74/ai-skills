#!/usr/bin/env python3
"""Bridge design-creator artifacts into the ai-workflows layout."""

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


def bridge_artifacts(jira_key: str, docs_repo_path: str | None) -> int:
    """Bridge design artifacts into ai-workflows layout.

    Args:
        jira_key: The Jira issue key (e.g., OSAC-1234)
        docs_repo_path: Optional docs repo path for config.json

    Returns:
        0 on success, 1 on error
    """
    root = repo_root()

    # Create .artifacts/design/{KEY}/ directory
    design_artifact_dir = root / ".artifacts" / "design" / jira_key
    design_artifact_dir.mkdir(parents=True, exist_ok=True)

    # Copy design file: artifacts/design-tasks/{KEY}-design.md → .artifacts/design/{KEY}/03-design.md
    source_design = root / "artifacts" / "design-tasks" / f"{jira_key}-design.md"
    target_design = design_artifact_dir / "03-design.md"

    if not source_design.exists():
        print(f"Error: Design file not found: {source_design}", file=sys.stderr)
        return 1

    target_design.write_text(source_design.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Copied design: {source_design} → {target_design}")

    # Copy source file if exists: artifacts/design-tasks/{KEY}-source.md → .artifacts/design/{KEY}/01-source.md
    source_jira = root / "artifacts" / "design-tasks" / f"{jira_key}-source.md"
    if source_jira.exists():
        target_jira = design_artifact_dir / "01-source.md"
        target_jira.write_text(source_jira.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Copied source: {source_jira} → {target_jira}")

    # Copy PRD if exists: artifacts/design-tasks/{KEY}-prd.md → .artifacts/prd/{KEY}/03-prd.md
    source_prd = root / "artifacts" / "design-tasks" / f"{jira_key}-prd.md"
    if source_prd.exists():
        prd_artifact_dir = root / ".artifacts" / "prd" / jira_key
        prd_artifact_dir.mkdir(parents=True, exist_ok=True)
        target_prd = prd_artifact_dir / "03-prd.md"
        target_prd.write_text(source_prd.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Copied PRD: {source_prd} → {target_prd}")

    # Create .artifacts/prd/config.json if docs_repo_path provided
    if docs_repo_path:
        prd_dir = root / ".artifacts" / "prd"
        prd_dir.mkdir(parents=True, exist_ok=True)
        config_file = prd_dir / "config.json"

        # Resolve to absolute path
        docs_path = Path(docs_repo_path).resolve()

        # Validate it exists and is a git repo
        if not docs_path.exists():
            print(f"Error: Docs repo path does not exist: {docs_path}", file=sys.stderr)
            return 1

        try:
            result = subprocess.run(
                ["git", "-C", str(docs_path), "remote", "get-url", "origin"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            docs_repo_remote = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print(f"Error: Could not get git remote from {docs_path}", file=sys.stderr)
            return 1

        config = {
            "docs_repo_path": str(docs_path),
            "docs_repo_remote": docs_repo_remote,
        }
        config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Created config: {config_file}")

    # Call provenance capture
    provenance_script = Path.home() / ".ai-workflows" / "_shared" / "scripts" / "provenance.py"
    if not provenance_script.exists():
        print(f"Warning: Provenance script not found at {provenance_script}", file=sys.stderr)
        print("Skipping provenance capture", file=sys.stderr)
        return 0

    try:
        subprocess.run(
            [
                sys.executable,
                str(provenance_script),
                "capture",
                "--workflow", "design",
                "--issue", jira_key,
                "--phase", "draft",
                "--authoring-mode", "skill",
            ],
            check=True,
            cwd=str(root),
            timeout=30,
        )
        print(f"Captured provenance: design/{jira_key} phase=draft")
    except subprocess.CalledProcessError as e:
        print(f"Error capturing provenance: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("Error: Provenance capture timed out", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bridge design-creator artifacts into ai-workflows layout"
    )
    parser.add_argument("jira_key", help="Jira issue key (e.g., OSAC-1234)")
    parser.add_argument(
        "--docs-repo",
        help="Path to enhancement-proposals repo (for config.json)",
    )

    args = parser.parse_args()

    return bridge_artifacts(args.jira_key, args.docs_repo)


if __name__ == "__main__":
    sys.exit(main())
