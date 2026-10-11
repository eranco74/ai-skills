#!/usr/bin/env python3
"""Run artifact checks and a separate semantic reviewer before accepting a draft.

Commands are JSON argv arrays, executed without a shell. The reviewer reads a
sealed JSON packet on stdin and returns the review JSON on stdout. This gate
never publishes documents or supplies feature-owner approval.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from research_context import check_artifacts, load_record


PROMPT = Path(__file__).parents[1] / "prompts" / "review-evidence.md"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def command_from_file(path):
    argv = json.loads(Path(path).read_text())
    if not isinstance(argv, list) or not argv or any(
            not isinstance(arg, str) or not arg or "\x00" in arg for arg in argv):
        raise ValueError("command file must contain a nonempty JSON argv array")
    return argv


def build_packet(record, files, reviewer_id):
    """Include original scope and primary captures, not just model extraction."""
    required = {"source", "record", "brief", "document", "coverage"}
    if record["stage"] == "design":
        required.add("approved_prd")
    required.update("source:" + source["id"] for source in record["sources"]
                    if source["verification"] == "verified")
    missing = required - files.keys()
    if missing:
        raise ValueError("missing semantic-review inputs: " + ", ".join(sorted(missing)))
    artifacts = {}
    for name, path in files.items():
        raw = Path(path).read_bytes()
        artifacts[name] = {"sha256": hashlib.sha256(raw).hexdigest(),
                           "text": raw.decode("utf-8")}
    if json.loads(artifacts["record"]["text"]) != record:
        raise ValueError("research record changed while preparing review")
    if not artifacts["source"]["text"].strip():
        raise ValueError("original scope source must not be empty")
    heading = re.match(r"\s*# ([A-Z][A-Z0-9_]*-\d+)\b", artifacts["source"]["text"])
    if heading and heading[1] != record["feature_key"]:
        raise ValueError("original scope header identifies a different feature")
    if record["stage"] == "design" and not artifacts["approved_prd"]["text"].strip():
        raise ValueError("approved PRD must not be empty")
    packet = {"schema_version": 1,
              **{key: record[key] for key in ("feature_key", "stage", "run_id")},
              "reviewer_id": reviewer_id, "record": record,
              "instructions": PROMPT.read_text(), "artifacts": artifacts}
    packet["input_sha256"] = digest(packet)
    return packet


def validate_review(review, packet):
    """Validate accounting and evidence quotations; the reviewer judges meaning."""
    errors = []
    if not isinstance(review, dict):
        return ["semantic review must be an object"]
    for field in ("schema_version", "feature_key", "stage", "run_id",
                  "input_sha256", "reviewer_id"):
        if type(review.get(field)) is not type(packet[field]) or review.get(field) != packet[field]:
            errors.append("semantic review " + field + " does not match this packet")

    def evidence(row, *, primary_ids=None, draft=False, obligation=False):
        refs = row.get("evidence")
        if not isinstance(refs, list) or not refs:
            errors.append("review verdict needs evidence quotations")
            return
        has_primary = False
        has_draft = False
        has_obligation = False
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append("review evidence must be an object")
                continue
            name, quote = ref.get("artifact"), ref.get("quote")
            artifact = packet["artifacts"].get(name) if isinstance(name, str) else None
            if not artifact or not isinstance(quote, str) or not quote.strip() or quote not in artifact["text"]:
                errors.append("review evidence must quote an actual input artifact")
            else:
                if name.startswith("source:"):
                    has_primary = primary_ids is None or name[7:] in primary_ids or has_primary
                if name == "document" or (name == "brief" and packet["stage"] == "prd"):
                    has_draft = True
                if name in {"source", "record", "approved_prd"}:
                    has_obligation = True
        if primary_ids is not None and not has_primary:
            errors.append("supported claim needs a primary-source quotation")
        if draft and not has_draft:
            errors.append("covered requirement needs a draft or verification-handoff quotation")
        if obligation and not has_obligation:
            errors.append("omitted requirement needs a source-obligation quotation")

    expected_requirements = {row["id"] for row in packet["record"]["requirements"]}
    unsupported_rows = review.get("unsupported_extracted_requirements", [])
    unsupported_ids = set()
    if not isinstance(unsupported_rows, list):
        errors.append("unsupported extracted requirements must be a list")
    else:
        for row in unsupported_rows:
            if not isinstance(row, dict):
                errors.append("unsupported extracted requirement must be an object")
                continue
            rid = row.get("id")
            if not isinstance(rid, str) or rid not in expected_requirements or rid in unsupported_ids:
                errors.append("unsupported extracted requirement IDs must match inputs exactly once")
            else:
                unsupported_ids.add(rid)
            if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
                errors.append("unsupported extracted requirement needs a rationale")
            evidence(row, obligation=True)
    inventory = review.get("source_obligations")
    mapped = set()
    if not isinstance(inventory, list) or not inventory:
        errors.append("semantic review needs an independent source-obligation inventory")
    else:
        for obligation in inventory:
            if not isinstance(obligation, dict):
                errors.append("source obligation must be an object")
                continue
            if not isinstance(obligation.get("statement"), str) or not obligation["statement"].strip():
                errors.append("source obligation needs a statement")
            refs = obligation.get("requirement_ids")
            if not isinstance(refs, list) or any(not isinstance(rid, str) or rid not in expected_requirements for rid in refs):
                errors.append("source obligation has invalid requirement IDs")
            else:
                mapped.update(refs)
            evidence(obligation)
            quotations = obligation.get("evidence", [])
            scope_names = {"source", "approved_prd"} if packet["stage"] == "design" else {"source"}
            if not isinstance(quotations, list) or not any(isinstance(q, dict) and isinstance(q.get("artifact"), str) and q["artifact"] in scope_names for q in quotations):
                errors.append("source inventory must quote the original scope input")
        if mapped & unsupported_ids:
            errors.append("extracted requirement cannot be both source-mapped and unsupported")
        if mapped | unsupported_ids != expected_requirements:
            errors.append("source inventory must map every extracted requirement ID or explicitly declare it unsupported")

    cited = set(re.findall(r"\[Chai:([^\]]+)\]", packet["artifacts"]["document"]["text"]))
    claims = {row["id"]: row for row in packet["record"]["claims"]}
    for field, expected, choices in (
            ("requirements", {row["id"] for row in packet["record"]["requirements"]},
             {"covered", "unresolved", "omitted", "violated"}),
            ("claims", cited, {"supported", "unsupported", "unverified"})):
        rows = review.get(field)
        if not isinstance(rows, list):
            errors.append("semantic review " + field + " must be a list")
            continue
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                errors.append("semantic verdict must be an object")
                continue
            rid = row.get("id")
            if not isinstance(rid, str) or rid not in expected or rid in seen:
                errors.append("semantic verdict IDs must match their inputs exactly")
            else:
                seen.add(rid)
            if not isinstance(row.get("status"), str) or row["status"] not in choices:
                errors.append("invalid semantic verdict")
            if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
                errors.append("semantic verdict needs a rationale")
            refs = None
            if field == "claims" and row.get("status") == "supported":
                refs = set(claims.get(rid, {}).get("source_ids", [])) if isinstance(rid, str) else set()
            evidence(row, primary_ids=refs,
                     draft=field == "requirements" and row.get("status") == "covered",
                     obligation=field == "requirements" and row.get("status") == "omitted")
        if seen != expected:
            errors.append("semantic review must account for every " + field + " ID")
    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("semantic findings must be a list")
    else:
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("severity"), str) or finding["severity"] not in {"minor", "major", "blocking"} or not isinstance(finding.get("description"), str) or not finding["description"].strip():
                errors.append("invalid semantic finding")
            else:
                evidence(finding)
    questions = review.get("owner_questions")
    if not isinstance(questions, list) or any(not isinstance(q, str) or not q.strip() for q in questions):
        errors.append("owner_questions must be a list of material unresolved decisions")
    return errors


def review_result(review, packet):
    errors = validate_review(review, packet)
    if errors:
        return {"valid": False, "errors": errors, "ready_for_owner_review": False,
                "owner_approval_required": True}
    # An explicit out-of-scope boundary must also be covered (respected).
    pending = [row["id"] for row in review["requirements"] if row["status"] != "covered"]
    unsupported = [row["id"] for row in review["claims"] if row["status"] != "supported"]
    major = [finding for finding in review["findings"] if finding["severity"] in {"major", "blocking"}]
    missing = [item["statement"] for item in review["source_obligations"] if not item["requirement_ids"]]
    unsupported_requirements = review.get("unsupported_extracted_requirements", [])
    return {"valid": True, "errors": [], "pending_requirements": pending,
            "unsupported_claims": unsupported, "blocking_findings": major,
            "unextracted_source_obligations": missing,
            "unsupported_extracted_requirements": unsupported_requirements,
            "owner_questions": review["owner_questions"],
            "ready_for_owner_review": not pending and not unsupported and not major and not missing and not unsupported_requirements and not review["owner_questions"],
            "owner_approval_required": True}


def run_command(argv, output_dir, name, timeout, *, stdin=None):
    started = time.monotonic()
    try:
        result = subprocess.run(argv, input=stdin, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        for stream in ("stdout", "stderr"):
            partial = getattr(exc, stream, None) or ""
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", errors="replace")
            (output_dir / (name + "-" + stream + ".txt")).write_text(partial)
        (output_dir / (name + "-execution.json")).write_text(json.dumps({
            "argv_sha256": digest(argv), "exit_code": "timeout",
            "duration_seconds": time.monotonic() - started}, indent=2) + "\n")
        raise
    (output_dir / (name + "-stdout.txt")).write_text(result.stdout)
    (output_dir / (name + "-stderr.txt")).write_text(result.stderr)
    (output_dir / (name + "-execution.json")).write_text(json.dumps({
        "argv_sha256": digest(argv), "exit_code": result.returncode,
        "duration_seconds": time.monotonic() - started}, indent=2) + "\n")
    if result.returncode:
        raise ValueError(name + " command failed; inspect its saved output")
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("record", "brief", "document", "coverage", "source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--approved-prd", type=Path)
    parser.add_argument("--source-capture", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--stage", choices=("prd", "design"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=("off", "live", "replay"), required=True)
    parser.add_argument("--forge-prd", action="store_true")
    parser.add_argument("--generator-id", required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--generation-command", type=Path)
    parser.add_argument("--review-command", type=Path, required=True)
    parser.add_argument("--command-timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    # Never reuse another invocation's review or acceptance decision.
    if args.output.exists():
        parser.error("output directory must be new for each gate invocation")
    args.output.mkdir(parents=True)
    result = {"valid": False, "ready_for_owner_review": False,
              "owner_approval_required": True}
    try:
        if not args.generator_id.strip() or not args.reviewer_id.strip() or args.generator_id == args.reviewer_id:
            raise ValueError("generator and reviewer must have distinct nonempty run identities")
        if args.command_timeout <= 0:
            raise ValueError("command timeout must be positive")
        review_command = command_from_file(args.review_command)
        scope_inputs = {"source": args.source}
        if args.approved_prd:
            scope_inputs["approved_prd"] = args.approved_prd
        scope_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for name, path in scope_inputs.items()}
        (args.output / "invocation.json").write_text(json.dumps({
            "feature_key": args.feature, "stage": args.stage, "run_id": args.run_id,
            "research_mode": args.mode, "generator_id": args.generator_id,
            "reviewer_id": args.reviewer_id, "scope_input_sha256": scope_hashes,
            "review_command_sha256": digest(review_command)}, indent=2) + "\n")
        if args.generation_command:
            if any(path.exists() for path in (args.record, args.brief, args.document, args.coverage)):
                raise ValueError("generation output paths must be fresh")
            run_command(command_from_file(args.generation_command), args.output,
                        "generation", args.command_timeout)
        if any(hashlib.sha256(path.read_bytes()).hexdigest() != scope_hashes[name]
               for name, path in scope_inputs.items()):
            raise ValueError("authoritative scope input changed during generation")
        record = load_record(args.record, feature=args.feature, stage=args.stage,
                             run_id=args.run_id, mode=args.mode)
        coverage = json.loads(args.coverage.read_text())
        mechanical = check_artifacts(record, args.brief.read_text(),
                                     args.document.read_text(), coverage,
                                     forge_prd=args.forge_prd)
        (args.output / "mechanical.json").write_text(json.dumps(mechanical, indent=2) + "\n")
        if not mechanical["ready_for_semantic_review"]:
            result = {**result, "mechanical": mechanical}
        else:
            files = {name: getattr(args, name) for name in
                     ("source", "record", "brief", "document", "coverage")}
            if args.approved_prd:
                files["approved_prd"] = args.approved_prd
            for capture in args.source_capture:
                sid, sep, path = capture.partition("=")
                if not sep or not sid or not path or "source:" + sid in files:
                    raise ValueError("source captures must be unique ID=PATH pairs")
                files["source:" + sid] = Path(path)
            packet = build_packet(record, files, args.reviewer_id)
            # Validate exactly the snapshot the reviewer will consume.
            snapshot_check = check_artifacts(record, packet["artifacts"]["brief"]["text"],
                packet["artifacts"]["document"]["text"],
                json.loads(packet["artifacts"]["coverage"]["text"]), forge_prd=args.forge_prd)
            if not snapshot_check["ready_for_semantic_review"]:
                raise ValueError("artifact snapshot no longer passes mechanical checks")
            (args.output / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
            raw = run_command(review_command, args.output, "review", args.command_timeout,
                              stdin=json.dumps(packet))
            review = json.loads(raw)
            (args.output / "review.json").write_text(json.dumps(review, indent=2) + "\n")
            result = review_result(review, packet)
            # A review only applies to the exact files it saw, including inputs.
            for name, path in files.items():
                if hashlib.sha256(path.read_bytes()).hexdigest() != packet["artifacts"][name]["sha256"]:
                    result = {"valid": False, "errors": ["input changed during semantic review: " + name],
                              "ready_for_owner_review": False, "owner_approval_required": True}
                    break
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc) if not isinstance(exc, subprocess.TimeoutExpired) else "command timed out"
    (args.output / "decision.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["ready_for_owner_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
