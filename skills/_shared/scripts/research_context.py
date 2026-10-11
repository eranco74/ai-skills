#!/usr/bin/env python3
"""Validate and render persisted organizational research without network calls."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


STATES = {"accepted", "proposed", "implemented", "superseded", "unknown"}
STATUSES = {"available", "unavailable", "timeout", "skipped"}
MODES = {"live", "replay", "off"}
MAX_RECORD_BYTES = 65536


def validate_record(record, *, feature=None, stage=None, run_id=None, mode=None):
    errors = []
    if not isinstance(record, dict):
        return ["record must be an object"]
    if type(record.get("schema_version")) is not int or record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for field in ("feature_key", "run_id"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append(f"{field} must be a nonempty string")
    for field, expected in (("feature_key", feature), ("stage", stage), ("run_id", run_id), ("research_mode", mode)):
        if expected is not None and record.get(field) != expected:
            errors.append(f"{field} does not match this run")
    for field, choices in (("stage", {"prd", "design"}), ("research_mode", MODES), ("status", STATUSES)):
        if not isinstance(record.get(field), str) or record.get(field) not in choices:
            errors.append(f"invalid {field}")
    if record.get("research_mode") == "off" and record.get("status") != "skipped":
        errors.append("off mode must record skipped retrieval")
    sections = {}
    for field in ("sources", "requirements", "claims", "conflicts", "questions"):
        value = record.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} must be a list")
            value = []
        sections[field] = value
    source_ids = set()
    for source in sections["sources"]:
        if not isinstance(source, dict):
            errors.append("source must be an object")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in source_ids:
            errors.append("source IDs must be nonempty and unique")
        else:
            source_ids.add(sid)
        url = source.get("url", "")
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            if parsed is None or parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username:
                errors.append(f"source {sid} needs an HTTP(S) URL without credentials")
        except ValueError:
            errors.append(f"source {sid} has an invalid URL")
        if not isinstance(source.get("verification"), str) or source.get("verification") not in {"verified", "unverified"}:
            errors.append(f"invalid verification for source {sid}")
        date = source.get("date")
        if date is not None:
            try:
                if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", date):
                    raise ValueError
                datetime.fromisoformat(date.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"source {sid} date must be ISO or null")
        if "revision" not in source or (source["revision"] is not None and not isinstance(source["revision"], str)):
            errors.append(f"source {sid} revision must be a string or null")
    for field in ("requirements", "claims", "conflicts"):
        ids = set()
        for item in sections[field]:
            if not isinstance(item, dict):
                errors.append(f"{field} items must be objects")
                continue
            iid = item.get("id")
            if not isinstance(iid, str) or not iid or iid in ids:
                errors.append(f"{field} IDs must be nonempty and unique")
            else:
                ids.add(iid)
            text = item.get("description" if field == "conflicts" else "statement")
            if not isinstance(text, str) or not text.strip():
                errors.append(f"{field} {iid} has no text")
            refs = item.get("source_ids")
            if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in source_ids for ref in refs):
                errors.append(f"{field} {iid} has invalid source references")
            elif field != "conflicts" and not refs:
                errors.append(f"{field} {iid} needs source references")
            if field == "requirements" and (not isinstance(item.get("scope"), str) or item.get("scope") not in {"in", "out", "constraint"}):
                errors.append(f"invalid scope for {iid}")
            if field == "claims" and (not isinstance(item.get("decision_state"), str) or item.get("decision_state") not in STATES):
                errors.append(f"invalid decision state for {iid}")
            if field == "conflicts" and any(type(item.get(k)) is not bool for k in ("material", "resolved")):
                errors.append(f"conflict {iid} must declare material and resolved")
    if any(not isinstance(q, str) or not q.strip() for q in sections["questions"]):
        errors.append("questions must be nonempty strings")
    return errors


def load_record(path, **identity):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError("record exceeds 64 KiB; curate a bounded brief")
    record = json.loads(raw)
    errors = validate_record(record, **identity)
    if errors:
        raise ValueError("; ".join(errors))
    return record


def readiness(record):
    conflicts = [c["id"] for c in record["conflicts"] if c["material"] and not c["resolved"]]
    return {"blocked_by_material_conflicts": conflicts, "research_status": record["status"]}


def validate_coverage(coverage, record):
    """Check the reviewer's coverage accounting, not the truth of its verdicts."""
    errors = []
    if not isinstance(coverage, dict):
        return ["coverage must be an object"]
    if type(coverage.get("schema_version")) is not int or coverage.get("schema_version") != 1:
        errors.append("coverage schema_version must be 1")
    for field in ("feature_key", "stage", "run_id"):
        if coverage.get(field) != record.get(field):
            errors.append(f"coverage {field} does not match this run")
    rows = coverage.get("requirements")
    if not isinstance(rows, list):
        return errors + ["coverage requirements must be a list"]
    expected = {r["id"] for r in record["requirements"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append("coverage items must be objects")
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or rid not in expected or rid in seen:
            errors.append("coverage IDs must be unique and refer to this record")
        else:
            seen.add(rid)
        if not isinstance(row.get("status"), str) or row.get("status") not in {"covered", "unresolved", "omitted"}:
            errors.append("invalid coverage status")
        if not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
            errors.append("coverage must cite a draft passage, handoff, or question")
    if seen != expected:
        errors.append("coverage must account for every requirement ID")
    return errors


def coverage_template(record):
    """Create exact-schema scaffolding without claiming any requirement passed."""
    errors = validate_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    return {"schema_version": 1, "feature_key": record["feature_key"],
            "stage": record["stage"], "run_id": record["run_id"],
            "requirements": [{"id": r["id"], "status": "unresolved",
                              "evidence": "Awaiting review of the draft or verification handoff"}
                             for r in record["requirements"]]}


def check_artifacts(record, brief, document, coverage, *, forge_prd=False):
    """Fail closed on missing sidecars/format; source truth needs separate review."""
    errors = validate_record(record)
    if errors:
        return {"valid": False, "errors": errors, "ready_for_semantic_review": False,
                "semantic_review_required": True}
    errors += validate_coverage(coverage, record)
    if errors:
        return {"valid": False, "errors": errors, "ready_for_semantic_review": False,
                "semantic_review_required": True}
    if not brief.strip() or record["run_id"] not in brief:
        errors.append("brief is empty or does not identify this run")
    if not document.lstrip().startswith("# "):
        errors.append("document must start with its title, without commentary")
    if forge_prd:
        headings = re.findall(r"^## (.+)$", document, re.M)
        expected = ["Problem Statement", "In Scope", "Out of Scope", "User Stories", "Assumptions", "Dependencies"]
        if headings != expected:
            errors.append("Forge PRD must contain the six template sections in order")
    claims = {c["id"]: c for c in record["claims"]}
    sources = {s["id"]: s for s in record["sources"]}
    for cid in re.findall(r"\[Chai:([^\]]+)\]", document):
        claim = claims.get(cid)
        if claim is None:
            errors.append(f"unknown draft claim ID {cid}")
            continue
        for sid in claim["source_ids"]:
            source = sources.get(sid, {})
            if source.get("verification") != "verified":
                errors.append(f"claim {cid} uses unverified source {sid}")
        if not any(sources[sid]["url"] in document for sid in claim["source_ids"]):
            errors.append(f"claim {cid} lacks an original-source link")
    material = {r["id"] for r in record["requirements"] if r["scope"] in {"in", "constraint"}}
    rows = coverage.get("requirements", []) if isinstance(coverage, dict) else []
    rows = rows if isinstance(rows, list) else []
    pending = [r["id"] for r in rows
               if isinstance(r, dict) and r.get("id") in material and r.get("status") != "covered"]
    conflicts = readiness(record)["blocked_by_material_conflicts"]
    return {"valid": not errors, "errors": errors, "pending_requirements": pending,
            "blocked_by_material_conflicts": conflicts,
            "ready_for_semantic_review": not errors and not pending and not conflicts,
            "semantic_review_required": True}


def render_record(record, max_chars=16000):
    errors = validate_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    sources = {s["id"]: s for s in record["sources"]}

    def references(item):
        return ", ".join(f"[{sid}]({sources[sid]['url']})" for sid in item["source_ids"])

    def verified(item):
        return all(sources[sid]["verification"] == "verified" for sid in item["source_ids"])

    lines = [f"# Evidence for {record['feature_key']} ({record['stage']})",
             f"Run: {record['run_id']}; mode: {record['research_mode']}; research: {record['status']}",
             "\n## Conflicts and questions"]
    for conflict in record["conflicts"]:
        state = "resolved" if conflict["resolved"] else "unresolved"
        material = "material" if conflict["material"] else "nonmaterial"
        lines.append(f"- {conflict['id']} ({material}, {state}): {conflict['description']} {references(conflict)}")
    lines.extend(f"- {question}" for question in record["questions"])
    if not record["conflicts"] and not record["questions"]:
        lines.append("No conflicts or questions recorded; this is not proof that none exist.")
    lines.append("\n## Explicit requirements and applicable owner decisions")
    excluded = []
    for requirement in record["requirements"]:
        if verified(requirement):
            lines.append(f"- {requirement['id']} [{requirement['scope']}]: {requirement['statement']} {references(requirement)}")
        else:
            excluded.append(requirement["id"])
    lines.append("\n## Verified organizational context")
    for claim in record["claims"]:
        if verified(claim):
            lines.append(f"- {claim['id']} [{claim['decision_state']}]: {claim['statement']} {references(claim)}")
        else:
            excluded.append(claim["id"])
    if excluded:
        lines.append("\nUnverified items excluded from factual input: " + ", ".join(excluded))
    lines.append("\n## Source revisions")
    for sid, source in sources.items():
        lines.append(f"- {sid}: {source['url']}; date: {source.get('date') or 'unknown'}; revision: {source.get('revision') or 'unknown'}; {source['verification']}")
    text = "\n".join(lines) + "\n"
    if len(text) > max_chars:
        raise ValueError("brief exceeds character budget; curate it without dropping conflicts")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render", "coverage-template", "check-artifacts"):
        command = sub.add_parser(name)
        command.add_argument("record", type=Path)
        command.add_argument("--feature")
        command.add_argument("--stage", choices=("prd", "design"))
        command.add_argument("--run-id")
        command.add_argument("--mode", choices=("off", "live", "replay"))
        if name == "render":
            command.add_argument("--output", type=Path)
            command.add_argument("--max-chars", type=int, default=16000)
        if name == "coverage-template":
            command.add_argument("--output", type=Path)
        if name == "check-artifacts":
            command.add_argument("--brief", type=Path, required=True)
            command.add_argument("--document", type=Path, required=True)
            command.add_argument("--coverage", type=Path, required=True)
            command.add_argument("--forge-prd", action="store_true")
    args = parser.parse_args()
    try:
        record = load_record(args.record, feature=args.feature, stage=args.stage, run_id=args.run_id, mode=args.mode)
        if args.command == "validate":
            print(json.dumps({"valid": True, **readiness(record)}))
        elif args.command == "coverage-template":
            text = json.dumps(coverage_template(record), indent=2) + "\n"
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text)
            else:
                print(text, end="")
        elif args.command == "check-artifacts":
            result = check_artifacts(record, args.brief.read_text(), args.document.read_text(),
                                     json.loads(args.coverage.read_text()), forge_prd=args.forge_prd)
            print(json.dumps(result))
            return 0 if result["ready_for_semantic_review"] else 1
        else:
            text = render_record(record, args.max_chars)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text)
            else:
                print(text, end="")
    except (ValueError, OSError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
