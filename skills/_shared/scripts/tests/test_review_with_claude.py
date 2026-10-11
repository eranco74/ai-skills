"""Tests for the isolated Claude CLI adapter using a mocked subprocess."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import review_with_claude  # noqa: E402


class ReviewWithClaudeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.packet = {
            "schema_version": 1,
            "feature_key": "OSAC-6285",
            "stage": "prd",
            "run_id": "run-6285",
            "input_sha256": "packet-hash-6285",
            "reviewer_id": "reviewer-run-1",
            "instructions": "Review only the attached packet.",
            "artifacts": {"document": {"text": "# Draft\n"}},
        }

    def tearDown(self):
        self.temp.cleanup()

    def response(self, *, returncode=0, stdout="", stderr=""):
        return type("Completed", (), {
            "returncode": returncode, "stdout": stdout, "stderr": stderr,
        })()

    def invoke(self, output_name, response, *, session_ids=None):
        output = self.root / output_name
        stdout = io.StringIO()
        stderr = io.StringIO()
        uuids = session_ids or [UUID("00000000-0000-4000-8000-000000000001")]
        with patch.object(review_with_claude.sys, "stdin", io.StringIO(json.dumps(self.packet))), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
             patch.object(review_with_claude.uuid, "uuid4", side_effect=uuids), \
             patch.object(review_with_claude.subprocess, "run", return_value=response) as run:
            code = review_with_claude.main([
                "--model", "test-model", "--output", str(output), "--timeout", "7",
            ])
        return code, stdout.getvalue(), stderr.getvalue(), run, output

    def test_each_call_uses_a_fresh_uuid_session_and_tool_free_strict_configuration(self):
        payload = {"structured_output": {"requirements": [], "claims": []}}
        responses = [self.response(stdout=json.dumps(payload)) for _ in range(2)]
        session_ids = [
            UUID("00000000-0000-4000-8000-000000000011"),
            UUID("00000000-0000-4000-8000-000000000022"),
        ]
        outputs = []
        commands = []
        for index, response in enumerate(responses):
            code, stdout, _, run, output = self.invoke(
                "call-" + str(index), response, session_ids=[session_ids[index]],
            )
            self.assertEqual(0, code)
            self.assertEqual(json.dumps(payload["structured_output"]) + "\n", stdout)
            commands.append(run.call_args.args[0])
            outputs.append(json.loads((output / "invocation.json").read_text()))

        expected_sessions = [str(value) for value in session_ids]
        self.assertEqual(expected_sessions, [item["session_id"] for item in outputs])
        self.assertNotEqual(outputs[0]["session_id"], outputs[1]["session_id"])
        for command, invocation in zip(commands, outputs):
            self.assertIn("--bare", command)
            self.assertIn("--strict-mcp-config", command)
            self.assertEqual([], invocation["tools"])
            self.assertEqual([], invocation["mcp_servers"])
            tools_index = command.index("--tools")
            self.assertEqual("", command[tools_index + 1])
            mcp_index = command.index("--mcp-config")
            self.assertEqual({"mcpServers": {}}, json.loads(command[mcp_index + 1]))
            session_index = command.index("--session-id")
            self.assertEqual(invocation["session_id"], command[session_index + 1])
            self.assertFalse(invocation["resumed_session"])

    def test_structured_output_is_extracted_and_packet_identity_is_schema_const(self):
        review = {
            "schema_version": 1, "feature_key": "OSAC-6285", "stage": "prd",
            "run_id": "run-6285", "input_sha256": "packet-hash-6285",
            "reviewer_id": "reviewer-run-1", "requirements": [], "claims": [],
        }
        envelope = {"type": "result", "structured_output": review, "result": "discard me"}
        code, stdout, _, run, output = self.invoke("structured", self.response(stdout=json.dumps(envelope)))
        self.assertEqual(0, code)
        self.assertEqual(review, json.loads(stdout))
        self.assertNotIn("discard me", stdout)
        self.assertEqual(envelope, json.loads((output / "response.json").read_text()))

        schema = review_with_claude.schema(self.packet)
        properties = schema["properties"]
        for field in ("schema_version", "feature_key", "stage", "run_id", "input_sha256", "reviewer_id"):
            self.assertEqual({"const": self.packet[field]}, properties[field])
            self.assertIn(field, schema["required"])
        self.assertFalse(schema["additionalProperties"])
        command = run.call_args.args[0]
        schema_index = command.index("--json-schema")
        self.assertEqual(schema, json.loads(command[schema_index + 1]))
        invocation = json.loads((output / "invocation.json").read_text())
        self.assertEqual(self.packet["input_sha256"], invocation["input_sha256"])

    def test_nested_schema_requires_strict_verdict_and_source_obligation_shapes(self):
        schema = review_with_claude.schema(self.packet)
        source_item = schema["properties"]["source_obligations"]["items"]
        requirement_item = schema["properties"]["requirements"]["items"]
        claim_item = schema["properties"]["claims"]["items"]
        finding_item = schema["properties"]["findings"]["items"]

        self.assertFalse(source_item["additionalProperties"])
        self.assertEqual(["statement", "requirement_ids", "evidence"], source_item["required"])
        self.assertEqual(["source"], source_item["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"])
        self.assertFalse(requirement_item["additionalProperties"])
        self.assertEqual(["covered", "unresolved", "omitted", "violated"],
                         requirement_item["properties"]["status"]["enum"])
        self.assertEqual(["document"], requirement_item["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"])
        self.assertEqual(["supported", "unsupported", "unverified"],
                         claim_item["properties"]["status"]["enum"])
        self.assertEqual(["document"], claim_item["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"])
        self.assertEqual(["minor", "major", "blocking"],
                         finding_item["properties"]["severity"]["enum"])
        for item in (source_item, requirement_item, claim_item, finding_item):
            self.assertFalse(item["additionalProperties"])
            self.assertEqual(list(item["properties"]), item["required"])

        design_packet = {**self.packet, "stage": "design"}
        design_schema = review_with_claude.schema(design_packet)
        design_source_artifacts = design_schema["properties"]["source_obligations"]["items"]["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"]
        self.assertEqual(["source", "approved_prd"], design_source_artifacts)

    def test_cli_errors_and_malformed_or_missing_output_fail_without_json_stdout(self):
        cases = [
            ("cli-error", self.response(returncode=2, stdout="{}", stderr="CLI failed")),
            ("malformed-json", self.response(stdout="{not json")),
            ("malformed-result-list", self.response(stdout=json.dumps(["not an event object"]))),
            ("no-structured-output", self.response(stdout=json.dumps({"type": "result", "result": "text"}))),
            ("reported-error", self.response(stdout=json.dumps({"is_error": True, "structured_output": {}}))),
        ]
        for name, response in cases:
            with self.subTest(name=name):
                code, stdout, stderr, _, output = self.invoke(name, response)
                self.assertEqual(1, code)
                self.assertEqual("", stdout)
                self.assertTrue(stderr.strip())
                self.assertTrue((output / "response.json").exists())
                self.assertTrue((output / "stderr.txt").exists())


if __name__ == "__main__":
    unittest.main()
