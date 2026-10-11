#!/usr/bin/env python3
"""Fresh, tool-free Claude CLI adapter for review_gate's stdin/stdout contract."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid


def schema(packet):
    properties = {key: {"const": packet[key]} for key in
                  ("schema_version", "feature_key", "stage", "run_id", "input_sha256", "reviewer_id")}

    def obj(fields):
        return {"type": "object", "properties": fields,
                "required": list(fields), "additionalProperties": False}

    def quoted(names):
        return {"type": "array", "minItems": 1, "items": obj({
            "artifact": {"type": "string", "enum": names},
            "quote": {"type": "string", "minLength": 1}})}

    scope_names = ["source", "approved_prd"] if packet["stage"] == "design" else ["source"]
    properties["source_obligations"] = {"type": "array", "minItems": 1,
        "items": obj({"statement": {"type": "string", "minLength": 1},
                      "requirement_ids": {"type": "array", "items": {"type": "string"}},
                      "evidence": quoted(scope_names)})}
    for field, statuses in (("requirements", ["covered", "unresolved", "omitted", "violated"]),
                            ("claims", ["supported", "unsupported", "unverified"])):
        properties[field] = {"type": "array", "items": obj({
            "id": {"type": "string", "minLength": 1},
            "status": {"type": "string", "enum": statuses},
            "rationale": {"type": "string", "minLength": 1},
            "evidence": quoted(list(packet["artifacts"]))})}
    properties["findings"] = {"type": "array", "items": obj({
        "severity": {"type": "string", "enum": ["minor", "major", "blocking"]},
        "description": {"type": "string", "minLength": 1},
        "evidence": quoted(list(packet["artifacts"]))})}
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
        session_id = str(uuid.uuid4())
        command = ["claude", "-p", "--bare", "--disable-slash-commands",
                   "--session-id", session_id, "--model", args.model,
                   "--effort", "medium", "--tools", "", "--strict-mcp-config",
                   "--mcp-config", '{"mcpServers":{}}', "--output-format", "json",
                   "--system-prompt", packet["instructions"],
                   "--json-schema", json.dumps(schema(packet))]
        (args.output / "invocation.json").write_text(json.dumps({
            "session_id": session_id, "model": args.model,
            "input_sha256": packet["input_sha256"], "tools": [],
            "mcp_servers": [], "bare": True, "resumed_session": False}, indent=2) + "\n")
        response = subprocess.run(command, input=json.dumps(packet), text=True,
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
        print(json.dumps(review))
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
