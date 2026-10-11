#!/usr/bin/env python3
"""Fresh, tool-free Claude CLI adapter for review_gate's stdin/stdout contract."""

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import uuid


SPAN_PROMPT = """Evidence format override for this review:
The `packet` below is the sealed review packet. Its `input_sha256` identifies
that original packet and must be copied unchanged into the review. The separate
`evidence_catalog` is a numbered view of the exact artifact text in that
packet. For every evidence item, return only `artifact`, `first_line`, and
`last_line`; both line numbers are 1-based and inclusive. Select a consecutive
range from one catalog artifact. Do not write a quote, paraphrase, normalize,
trim, or reconstruct text. The adapter will resolve each span to its exact
literal quote before passing the review to the gate. Use the schema's artifact
allowlist and do not cite line numbers outside that artifact's catalog.
"""


EVIDENCE_FIELDS = ("source_obligations", "requirements", "claims", "findings",
                   "unsupported_extracted_requirements")
IDENTITY_FIELDS = ("schema_version", "feature_key", "stage", "run_id",
                   "input_sha256", "reviewer_id")


def build_line_catalog(packet):
    """Number the exact artifact lines without changing the sealed packet."""
    artifacts = packet["artifacts"]
    catalog = {}
    for name, artifact in artifacts.items():
        lines = artifact["text"].splitlines(keepends=True)
        catalog[name] = {
            "line_count": len(lines),
            "lines": [{"line": number, "text": line}
                      for number, line in enumerate(lines, 1)],
        }
    return {"input_sha256": packet["input_sha256"], "stage": packet["stage"],
            "artifacts": catalog}


def resolve_review_spans(review, catalog):
    """Replace model-selected line spans with exact packet artifact quotes."""
    if not isinstance(review, dict):
        raise ValueError("structured review must be an object")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("artifacts"), dict):
        raise ValueError("evidence catalog is malformed")
    resolved = json.loads(json.dumps(review))
    for field in EVIDENCE_FIELDS:
        if field == "unsupported_extracted_requirements" and field not in resolved:
            continue  # Existing caller reviews remain compatible when every ID maps.
        rows = resolved.get(field)
        if not isinstance(rows, list):
            raise ValueError("structured review " + field + " must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("structured review verdict must be an object")
            spans = row.get("evidence")
            if not isinstance(spans, list) or not spans:
                raise ValueError("review evidence must contain at least one line span")
            quotes = []
            for span in spans:
                if not isinstance(span, dict) or set(span) != {"artifact", "first_line", "last_line"}:
                    raise ValueError("evidence span must identify an artifact and inclusive line range")
                name = span["artifact"]
                first, last = span["first_line"], span["last_line"]
                if not isinstance(name, str) or name not in catalog["artifacts"]:
                    raise ValueError("evidence span names an unknown artifact")
                if field == "source_obligations":
                    allowed = {"source"}
                    if catalog.get("stage") == "design":
                        allowed.add("approved_prd")
                    if name not in allowed:
                        raise ValueError("source obligation span names an invalid scope artifact")
                if type(first) is not int or type(last) is not int:
                    raise ValueError("evidence line numbers must be integers")
                lines = catalog["artifacts"][name]["lines"]
                if first < 1 or last < 1 or first > last or last > len(lines):
                    raise ValueError("evidence span is outside the artifact line range")
                quote = "".join(item["text"] for item in lines[first - 1:last])
                if not quote.strip():
                    raise ValueError("evidence span selects only blank text")
                quotes.append({"artifact": name, "quote": quote})
            row["evidence"] = quotes
    return resolved


def sha256_json(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def schema(packet):
    properties = {key: {"const": packet[key]} for key in
                  IDENTITY_FIELDS}

    def obj(fields):
        return {"type": "object", "properties": fields,
                "required": list(fields), "additionalProperties": False}

    def span_items(names):
        return {"type": "array", "minItems": 1, "items": obj({
            "artifact": {"type": "string", "enum": names},
            "first_line": {"type": "integer", "minimum": 1},
            "last_line": {"type": "integer", "minimum": 1}})}

    scope_names = ["source", "approved_prd"] if packet["stage"] == "design" else ["source"]
    requirement_ids = sorted(row["id"] for row in packet["record"]["requirements"])
    claim_ids = sorted(set(re.findall(r"\[Chai:([^\]]+)\]", packet["artifacts"]["document"]["text"])))

    def id_schema(ids):
        value = {"type": "string", "minLength": 1}
        if ids:
            value["enum"] = ids
        return value

    properties["source_obligations"] = {"type": "array", "minItems": 1,
        "items": obj({"statement": {"type": "string", "minLength": 1},
                      "requirement_ids": {"type": "array", "uniqueItems": True,
                                          "maxItems": len(requirement_ids), "items": id_schema(requirement_ids)},
                      "evidence": span_items(scope_names)})}
    for field, statuses in (("requirements", ["covered", "unresolved", "omitted", "violated"]),
                            ("claims", ["supported", "unsupported", "unverified"])):
        ids = requirement_ids if field == "requirements" else claim_ids
        properties[field] = {"type": "array", "minItems": len(ids), "maxItems": len(ids), "items": obj({
            "id": id_schema(ids),
            "status": {"type": "string", "enum": statuses},
            "rationale": {"type": "string", "minLength": 1},
            "evidence": span_items(list(packet["artifacts"]))})}
    properties["unsupported_extracted_requirements"] = {"type": "array",
        "maxItems": len(requirement_ids), "items": obj({
            "id": id_schema(requirement_ids),
            "rationale": {"type": "string", "minLength": 1},
            "evidence": span_items(["record", *scope_names])})}
    properties["findings"] = {"type": "array", "items": obj({
        "severity": {"type": "string", "enum": ["minor", "major", "blocking"]},
        "description": {"type": "string", "minLength": 1},
        "evidence": span_items(list(packet["artifacts"]))})}
    properties["owner_questions"] = {"type": "array", "items": {"type": "string"}}
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)
    if args.output.exists() or args.timeout <= 0:
        parser.error("use a fresh output directory and a positive timeout")
    args.output.mkdir(parents=True)
    try:
        packet = json.load(sys.stdin)
        catalog = build_line_catalog(packet)
        model_input = {"packet": packet, "evidence_catalog": catalog}
        (args.output / "evidence-catalog.json").write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
        session_id = str(uuid.uuid4())
        command = ["claude", "-p", "--bare", "--disable-slash-commands",
                   "--session-id", session_id, "--model", args.model,
                   "--effort", "medium", "--tools", "", "--strict-mcp-config",
                   "--mcp-config", '{"mcpServers":{}}', "--output-format", "json",
                   "--system-prompt", packet["instructions"] + "\n\n" + SPAN_PROMPT,
                   "--json-schema", json.dumps(schema(packet))]
        (args.output / "invocation.json").write_text(json.dumps({
            "session_id": session_id, "model": args.model,
            "input_sha256": packet["input_sha256"], "tools": [],
            "evidence_catalog_sha256": sha256_json(catalog),
            "mcp_servers": [], "bare": True, "resumed_session": False}, indent=2) + "\n")
        response = subprocess.run(command, input=json.dumps(model_input), text=True,
                                  capture_output=True, timeout=args.timeout,
                                  cwd=args.output, check=False)
        (args.output / "response.json").write_text(response.stdout)
        (args.output / "stderr.txt").write_text(response.stderr)
        if response.returncode:
            raise ValueError("reviewer CLI failed; inspect saved response")
        payload = json.loads(response.stdout)
        if isinstance(payload, list):
            payload = next((item for item in reversed(payload)
                            if isinstance(item, dict) and item.get("type") == "result"), {})
        if not isinstance(payload, dict) or payload.get("is_error"):
            raise ValueError("reviewer CLI returned an error")
        review = payload.get("structured_output")
        if not isinstance(review, dict):
            raise ValueError("reviewer CLI did not return a structured review")
        raw_review_path = args.output / "structured-review.json"
        raw_review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")
        provenance = {
            **{field: packet[field] for field in IDENTITY_FIELDS},
            "session_id": session_id,
            "model": args.model,
            "evidence_catalog_sha256": sha256_json(catalog),
            "structured_review_sha256": sha256_json(review),
        }
        try:
            resolved = resolve_review_spans(review, catalog)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError):
            provenance["span_resolution"] = "failed"
            (args.output / "provenance.json").write_text(
                json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
            raise
        provenance["span_resolution"] = "resolved"
        provenance["resolved_review_sha256"] = sha256_json(resolved)
        (args.output / "provenance.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(resolved, ensure_ascii=False))
        return 0
    except subprocess.TimeoutExpired as exc:
        def as_text(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        (args.output / "response.json").write_text(as_text(exc.stdout))
        (args.output / "stderr.txt").write_text(as_text(exc.stderr))
        print("Semantic reviewer failed: TimeoutExpired", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        # stdout is reserved for the semantic review object.
        print("Semantic reviewer failed: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
