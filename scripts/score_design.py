#!/usr/bin/env python3
"""
Deterministic scoring script for OSAC design documents.

Validates design documents against structural and content requirements.
All subcommands output JSON for programmatic consumption.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class DesignScorer:
    """Validates OSAC design documents against template requirements."""

    # Required sections from the OSAC design template
    # Handles numbered prefixes like "## 1. Summary"
    REQUIRED_SECTIONS = [
        "Summary",
        "Motivation",
        "Proposal",
        "Security Considerations",
        "Failure Handling and Recovery",
        "RBAC / Tenancy",
        "Observability and Monitoring",
        "Risks and Mitigations",
        "Drawbacks",
        "Alternatives",
        "Test Plan",
        "Graduation Criteria",
        "Upgrade / Downgrade Strategy",
        "Version Skew Strategy",
        "Support Procedures",
    ]

    # Alternative names for sections (case-insensitive matching)
    SECTION_ALIASES = {
        "Failure Handling and Recovery": ["Failure Handling"],
        "RBAC / Tenancy": ["RBAC", "Tenancy"],
        "Observability and Monitoring": ["Observability"],
        "Risks and Mitigations": ["Risks"],
        "Alternatives": ["Alternatives (Not Implemented)", "Alternatives Considered"],
        "Upgrade / Downgrade Strategy": ["Upgrade", "Upgrade / Downgrade"],
        "Version Skew Strategy": ["Version Skew"],
    }

    # Required subsections
    REQUIRED_SUBSECTIONS = {
        "Motivation": ["Goals", "Non-Goals"],
        "Proposal": [
            "Workflow Description",
            "API Extensions",
            "Implementation Details",
        ],
        "Test Plan": ["Unit Tests", "Integration Tests", "E2E Tests"],
    }

    # Required frontmatter fields
    REQUIRED_FRONTMATTER_FIELDS = [
        "title",
        "authors",
        "creation-date",
        "tracking-link",
        "prd",
    ]

    # Placeholder patterns
    PLACEHOLDER_PATTERNS = [
        r"^\s*TBD\s*$",
        r"^\s*TODO\s*$",
        r"^\s*N/A\s*$",
        r"^\s*None\s*$",
        r"^\s*-\s*$",
    ]

    def __init__(self, design_path: str):
        """Initialize scorer with design document path."""
        self.design_path = Path(design_path)
        if not self.design_path.exists():
            raise FileNotFoundError(f"Design file not found: {design_path}")

        self.content = self.design_path.read_text()
        self.lines = self.content.splitlines()

    def extract_frontmatter(self) -> Tuple[Dict[str, Any], List[str]]:
        """Extract YAML frontmatter from the design document.

        Returns:
            Tuple of (frontmatter_dict, content_lines_after_frontmatter)
        """
        if not self.lines or self.lines[0].strip() != "---":
            return {}, self.lines

        # Find closing delimiter
        end_idx = None
        for i in range(1, len(self.lines)):
            if self.lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return {}, self.lines

        # Parse YAML frontmatter (simple key: value parser)
        frontmatter = {}
        for line in self.lines[1:end_idx]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Handle key: value
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Handle list values (starting with -)
                if value.startswith("-"):
                    if key not in frontmatter:
                        frontmatter[key] = []
                    frontmatter[key].append(value[1:].strip())
                else:
                    frontmatter[key] = value
            # Handle list continuation
            elif line.startswith("-") and frontmatter:
                last_key = list(frontmatter.keys())[-1]
                if not isinstance(frontmatter[last_key], list):
                    frontmatter[last_key] = [frontmatter[last_key]]
                frontmatter[last_key].append(line[1:].strip())

        return frontmatter, self.lines[end_idx + 1 :]

    def extract_sections(self, lines: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract section hierarchy from markdown content.

        Returns:
            Dict mapping section names to {level, start_line, end_line, content}
        """
        sections = {}
        current_section = None
        section_stack = []

        for i, line in enumerate(lines):
            # Match markdown headers
            match = re.match(r"^(#{1,6})\s+(?:\d+\.)?\s*(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()

                # Close sections at same or higher level
                while section_stack and section_stack[-1]["level"] >= level:
                    closed = section_stack.pop()
                    closed["end_line"] = i - 1

                # Start new section
                section_info = {
                    "level": level,
                    "start_line": i,
                    "end_line": len(lines) - 1,  # Temporary, will be updated
                    "title": title,
                    "content": [],
                }
                sections[title] = section_info
                section_stack.append(section_info)
                current_section = section_info
            elif current_section:
                current_section["content"].append(line)

        return sections

    def normalize_section_name(self, name: str) -> str:
        """Normalize section name for matching (remove numbers, extra spaces)."""
        # Remove leading numbers like "1.", "2.1.", etc.
        normalized = re.sub(r"^\d+(\.\d+)*\.\s*", "", name)
        return normalized.strip()

    def check_structure(self) -> Dict[str, Any]:
        """Check if design has all required sections."""
        _, content_lines = self.extract_frontmatter()
        sections = self.extract_sections(content_lines)

        # Normalize section names
        normalized_sections = {
            self.normalize_section_name(name): name for name in sections.keys()
        }

        present_sections = []
        missing_sections = []
        issues = []

        # Check required sections
        for required in self.REQUIRED_SECTIONS:
            found = False

            # Check exact match (normalized)
            if required in normalized_sections:
                found = True
                present_sections.append(normalized_sections[required])
            else:
                # Check aliases
                for alias in self.SECTION_ALIASES.get(required, []):
                    if alias in normalized_sections:
                        found = True
                        present_sections.append(normalized_sections[alias])
                        break

            if not found:
                missing_sections.append(required)

        # Check required subsections — look for them anywhere in sections dict
        for parent, subsections in self.REQUIRED_SUBSECTIONS.items():
            parent_found = False
            for alias in [parent] + self.SECTION_ALIASES.get(parent, []):
                if alias in normalized_sections:
                    parent_found = True
                    break

            if parent_found:
                for subsection in subsections:
                    sub_found = False
                    sub_aliases = [subsection]
                    if subsection == "Implementation Details":
                        sub_aliases.extend(["Implementation Details/Notes/Constraints",
                                           "Implementation Details/Notes", "Implementation"])
                    for sa in sub_aliases:
                        if sa in normalized_sections:
                            sub_found = True
                            break
                        for norm_name in normalized_sections:
                            if sa.lower() in norm_name.lower():
                                sub_found = True
                                break
                        if sub_found:
                            break
                    if not sub_found:
                        issues.append(
                            f"Missing required subsection '{subsection}' (warning)"
                        )

        if missing_sections:
            issues.append(
                f"Missing required sections: {', '.join(missing_sections)}"
            )

        critical_issues = [i for i in issues if "(warning)" not in i]
        return {
            "pass": len(missing_sections) == 0 and len(critical_issues) == 0,
            "issues": issues,
            "missing_sections": missing_sections,
            "present_sections": present_sections,
        }

    def check_frontmatter(self) -> Dict[str, Any]:
        """Check if frontmatter has all required fields."""
        frontmatter, _ = self.extract_frontmatter()
        issues = []
        missing_fields = []

        for field in self.REQUIRED_FRONTMATTER_FIELDS:
            if field not in frontmatter:
                missing_fields.append(field)
                issues.append(f"Missing required frontmatter field: {field}")
            elif not frontmatter[field]:
                issues.append(f"Empty required frontmatter field: {field}")

        # Validate field types
        if "authors" in frontmatter and not isinstance(frontmatter["authors"], list):
            if not frontmatter["authors"].startswith("["):
                issues.append("Field 'authors' should be a list")

        return {
            "pass": len(issues) == 0,
            "issues": issues,
        }

    def detect_design_type(self) -> str:
        """Detect whether this is a UI design or backend design.

        Uses strong signals (component libraries, UI frameworks) weighted 2x
        and weak signals (mentions of UI repos) weighted 1x. Threshold: 5+.
        A backend design that mentions osac-ui in a CLI section won't trigger.
        """
        strong = ["patternfly", "tanstack", "formik", "useapiquery",
                  "useapifetch", "no backend changes", "ui-only"]
        weak = ["react", "osac-ui", "osac-ux", "typescript", "cypress", "frontend"]
        content_lower = self.content.lower()
        score = sum(2 for s in strong if s in content_lower)
        score += sum(1 for s in weak if s in content_lower)
        if score >= 5:
            return "ui"
        return "backend"

    def check_proto(self) -> Dict[str, Any]:
        """Check if design includes proto or TypeScript schema definitions."""
        design_type = self.detect_design_type()
        has_proto = False
        proto_count = 0
        has_typescript = False
        ts_count = 0

        in_proto_block = False
        in_ts_block = False
        for line in self.lines:
            if re.match(r"^```(protobuf|proto)\s*$", line):
                in_proto_block = True
                has_proto = True
                continue
            elif re.match(r"^```(typescript|ts|tsx)\s*$", line):
                in_ts_block = True
                has_typescript = True
                continue
            elif line.strip() == "```" and (in_proto_block or in_ts_block):
                if in_proto_block:
                    proto_count += 1
                if in_ts_block:
                    ts_count += 1
                in_proto_block = False
                in_ts_block = False
                continue

            if not in_proto_block and re.match(r"^\s*message\s+\w+", line):
                has_proto = True
                proto_count += 1
            if not in_ts_block and re.match(r"^\s*(export\s+)?(interface|type)\s+\w+", line):
                has_typescript = True
                ts_count += 1

        if design_type == "ui":
            has_schemas = has_proto or has_typescript
            return {
                "pass": has_schemas,
                "design_type": "ui",
                "has_proto": has_proto,
                "proto_count": proto_count,
                "has_typescript": has_typescript,
                "ts_count": ts_count,
            }

        return {
            "pass": has_proto,
            "design_type": "backend",
            "has_proto": has_proto,
            "proto_count": proto_count,
        }

    def check_tenant_isolation(self) -> Dict[str, Any]:
        """Check if design addresses tenant isolation."""
        design_type = self.detect_design_type()
        issues = []
        content_lower = self.content.lower()

        if design_type == "ui":
            has_isolation = ("tenant isolation" in content_lower or
                           "tenant" in content_lower and "isolat" in content_lower or
                           "osac.openshift.io/tenant" in content_lower)
            if not has_isolation:
                issues.append("Missing tenant isolation discussion (UI designs should explain how the API enforces isolation)")
            return {"pass": has_isolation, "design_type": "ui", "issues": issues}

        has_tenant = "osac.openshift.io/tenant" in content_lower
        has_owner = "osac.openshift.io/owner-reference" in content_lower
        if not has_tenant:
            issues.append("Missing tenant isolation annotation: osac.openshift.io/tenant")
        if not has_owner:
            issues.append("Missing owner reference annotation: osac.openshift.io/owner-reference")
        return {"pass": has_tenant and has_owner, "design_type": "backend", "issues": issues}

    def check_length(self) -> Dict[str, Any]:
        """Check if design is within expected length range."""
        non_blank_lines = sum(1 for line in self.lines if line.strip())
        issues = []

        if non_blank_lines < 150:
            issues.append(
                f"Design is very short ({non_blank_lines} lines). Expected 200-800 for substantive designs."
            )
        elif non_blank_lines > 1000:
            issues.append(
                f"Design is very long ({non_blank_lines} lines). Consider splitting or condensing."
            )
        elif non_blank_lines < 200:
            issues.append(
                f"Design is somewhat short ({non_blank_lines} lines). Typical range is 200-800."
            )

        return {
            "pass": 200 <= non_blank_lines <= 800,
            "lines": non_blank_lines,
            "issues": issues,
        }

    def check_placeholders(self) -> Dict[str, Any]:
        """Check for placeholder-only sections."""
        _, content_lines = self.extract_frontmatter()
        sections = self.extract_sections(content_lines)

        placeholder_sections = []

        for section_name, section_info in sections.items():
            content = "\n".join(section_info["content"]).strip()

            # Skip empty sections
            if not content:
                continue

            # Check if content is only placeholders
            content_lines = [line.strip() for line in content.split("\n") if line.strip()]
            if not content_lines:
                continue

            # Check if all non-empty lines are placeholders
            all_placeholders = True
            for line in content_lines:
                is_placeholder = False
                for pattern in self.PLACEHOLDER_PATTERNS:
                    if re.match(pattern, line, re.IGNORECASE):
                        is_placeholder = True
                        break
                if not is_placeholder:
                    all_placeholders = False
                    break

            if all_placeholders:
                placeholder_sections.append(section_name)

        return {
            "pass": len(placeholder_sections) == 0,
            "placeholder_sections": placeholder_sections,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Score OSAC design documents against template requirements"
    )
    parser.add_argument("design_file", help="Path to design markdown file")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser(
        "check-structure", help="Verify all required sections are present"
    )
    subparsers.add_parser(
        "check-frontmatter", help="Verify frontmatter has required fields"
    )
    subparsers.add_parser(
        "check-proto", help="Check if design includes proto definitions"
    )
    subparsers.add_parser(
        "check-tenant-isolation", help="Check for tenant isolation metadata"
    )
    subparsers.add_parser("check-length", help="Check design length")
    subparsers.add_parser(
        "check-placeholders", help="Check for placeholder-only sections"
    )

    args = parser.parse_args()

    try:
        scorer = DesignScorer(args.design_file)

        if args.subcommand == "check-structure":
            result = scorer.check_structure()
        elif args.subcommand == "check-frontmatter":
            result = scorer.check_frontmatter()
        elif args.subcommand == "check-proto":
            result = scorer.check_proto()
        elif args.subcommand == "check-tenant-isolation":
            result = scorer.check_tenant_isolation()
        elif args.subcommand == "check-length":
            result = scorer.check_length()
        elif args.subcommand == "check-placeholders":
            result = scorer.check_placeholders()
        else:
            print(
                json.dumps({"error": f"Unknown subcommand: {args.subcommand}"}),
                file=sys.stderr,
            )
            sys.exit(1)

        print(json.dumps(result, indent=2))
        sys.exit(0 if result["pass"] else 1)

    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
