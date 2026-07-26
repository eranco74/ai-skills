#!/usr/bin/env python3
"""Deterministic scoring utilities for PRD validation."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


REQUIRED_SECTIONS = [
    "Problem Statement",
    "In Scope",
    "Out of Scope",
    "User Stories"
]

OSAC_PERSONAS = [
    "Cloud Provider Admin",
    "Cloud Infrastructure Admin",
    "Tenant Admin",
    "Tenant User"
]

DESIGN_LEAKAGE_PATTERNS = [
    (r'\breconcil(?:er?|ation)\b', 'reconciler/reconciliation'),
    (r'\bfinalizer\b', 'finalizer'),
    (r'\bplaybook\b', 'playbook'),
    (r'\benv var\b', 'env var'),
    (r'\bAAP job\b', 'AAP job'),
    (r'\bCRD field\b', 'CRD field'),
    (r'\bosac-operator\b', 'osac-operator'),
    (r'\bosac-aap\b', 'osac-aap'),
    (r'\bansible role\b', 'ansible role'),
    (r'\bcontroller\b(?!\s+Planes?)', 'controller (not Hosted Control Planes)'),
]


def read_markdown(path: str) -> str:
    """Read markdown file, skipping frontmatter."""
    file_path = Path(path)

    if not file_path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text()

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            content = parts[2]

    return content


def extract_sections(content: str) -> Dict[str, str]:
    """Extract sections from markdown by heading."""
    sections = {}
    lines = content.split("\n")

    current_section = None
    section_lines = []

    for line in lines:
        heading_match = re.match(r"^#+\s+(.+)$", line)

        if heading_match:
            if current_section:
                sections[current_section] = "\n".join(section_lines).strip()

            current_section = heading_match.group(1).strip()
            section_lines = []
        elif current_section:
            section_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(section_lines).strip()

    return sections


def find_section(sections: Dict[str, str], target: str) -> bool:
    """Check if a section exists, handling numbered headings and aliases."""
    aliases = {
        "Problem Statement": ["Problem Statement"],
        "In Scope": ["In Scope", "Goals", "Goals and Non-Goals", "Functional Requirements", "Requirements"],
        "Out of Scope": ["Out of Scope", "Non-Goals", "Goals and Non-Goals"],
        "User Stories": ["User Stories", "User Scenarios", "Personas", "OSAC Dimensions"],
    }
    candidates = aliases.get(target, [target])
    target_lower_set = {c.lower() for c in candidates}
    for section_name in sections:
        clean = re.sub(r"^\d+\.?\s*", "", section_name).strip().lower()
        if clean in target_lower_set:
            return True
    return False


def check_structure(prd_path: str) -> Dict[str, Any]:
    """Verify PRD has required sections."""
    content = read_markdown(prd_path)
    sections = extract_sections(content)

    missing_sections = []
    empty_sections = []

    for required_section in REQUIRED_SECTIONS:
        if not find_section(sections, required_section):
            missing_sections.append(required_section)

    issues = []

    if missing_sections:
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")

    if empty_sections:
        issues.append(f"Empty required sections: {', '.join(empty_sections)}")

    result = {
        "pass": len(issues) == 0,
        "issues": issues
    }

    print(json.dumps(result, indent=2))
    return result


def check_personas(prd_path: str) -> Dict[str, Any]:
    """Verify user stories cover OSAC personas."""
    content = read_markdown(prd_path)

    user_stories_section = ""
    for line in content.split("\n"):
        heading_match = re.match(r"^#+\s+(?:\d+\.?\s*)?(.+)$", line)
        if heading_match:
            clean = heading_match.group(1).strip().lower()
            if clean in ("user stories", "user scenarios", "personas"):
                idx = content.index(line)
                user_stories_section = content[idx:]
                break

    if not user_stories_section:
        user_stories_section = content

    if not user_stories_section:
        result = {
            "pass": False,
            "issues": ["User Stories section is missing or empty"]
        }
        print(json.dumps(result, indent=2))
        return result

    found_personas = []
    missing_personas = []

    for persona in OSAC_PERSONAS:
        if persona.lower() in user_stories_section.lower():
            found_personas.append(persona)
        else:
            missing_personas.append(persona)

    issues = []

    if len(found_personas) == 0:
        issues.append("No OSAC personas found in User Stories section")

    if missing_personas and len(found_personas) > 0:
        issues.append(f"Missing personas: {', '.join(missing_personas)}")

    result = {
        "pass": len(missing_personas) == 0 and len(found_personas) > 0,
        "issues": issues
    }

    print(json.dumps(result, indent=2))
    return result


def check_leakage(prd_path: str) -> Dict[str, Any]:
    """Check for design leakage keywords."""
    content = read_markdown(prd_path)

    found_keywords = []

    for pattern, label in DESIGN_LEAKAGE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            found_keywords.append(f"{label} (found {len(matches)} time(s))")

    issues = []

    if found_keywords:
        issues.append("Design leakage detected - PRD contains implementation details:")
        issues.extend([f"  - {kw}" for kw in found_keywords])

    result = {
        "pass": len(found_keywords) == 0,
        "issues": issues
    }

    print(json.dumps(result, indent=2))
    return result


def check_duplicates(prd_path: str) -> Dict[str, Any]:
    """Detect near-duplicate user stories across persona sections."""
    content = read_markdown(prd_path)
    stories = re.findall(r'As a [^,]+, I want .+? so that .+?\.', content)
    if len(stories) < 2:
        return {"pass": True, "issues": []}

    duplicates = []
    for i in range(len(stories)):
        norm_a = re.sub(r'As a [^,]+,', 'As a PERSONA,', stories[i]).lower()
        words_a = set(norm_a.split())
        for j in range(i + 1, len(stories)):
            norm_b = re.sub(r'As a [^,]+,', 'As a PERSONA,', stories[j]).lower()
            words_b = set(norm_b.split())
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
            if overlap > 0.8:
                duplicates.append(
                    f"Near-duplicate stories: '{stories[i][:60]}...' and '{stories[j][:60]}...'"
                )

    result = {"pass": len(duplicates) == 0, "issues": duplicates}
    print(json.dumps(result, indent=2))
    return result


def check_length(prd_path: str) -> Dict[str, Any]:
    """Check PRD is within target length range."""
    content = read_markdown(prd_path)
    non_blank = len([l for l in content.split("\n") if l.strip()])
    issues = []
    if non_blank > 120:
        issues.append(f"PRD has {non_blank} non-blank lines (target: 40-80). Consider trimming.")
    elif non_blank < 25:
        issues.append(f"PRD has {non_blank} non-blank lines (target: 40-80). May be too sparse.")
    result = {"pass": 25 <= non_blank <= 120, "issues": issues}
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Deterministic scoring utilities for PRD validation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    structure_parser = subparsers.add_parser("check-structure", help="Verify PRD has required sections")
    structure_parser.add_argument("prd_file", help="Path to PRD markdown file")

    personas_parser = subparsers.add_parser("check-personas", help="Verify user stories cover OSAC personas")
    personas_parser.add_argument("prd_file", help="Path to PRD markdown file")

    leakage_parser = subparsers.add_parser("check-leakage", help="Check for design leakage keywords")
    leakage_parser.add_argument("prd_file", help="Path to PRD markdown file")

    dup_parser = subparsers.add_parser("check-duplicates", help="Detect near-duplicate user stories")
    dup_parser.add_argument("prd_file", help="Path to PRD markdown file")

    len_parser = subparsers.add_parser("check-length", help="Check PRD length is within range")
    len_parser.add_argument("prd_file", help="Path to PRD markdown file")

    args = parser.parse_args()

    checks = {
        "check-structure": check_structure,
        "check-personas": check_personas,
        "check-leakage": check_leakage,
        "check-duplicates": check_duplicates,
        "check-length": check_length,
    }
    fn = checks.get(args.command)
    if fn:
        result = fn(args.prd_file)
        sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
