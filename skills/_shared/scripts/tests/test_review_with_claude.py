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
            "artifacts": {
                "source": {"text": "Scope introduction.\nThe source obligation is R1.\n"},
                "record": {"text": "Requirement R1 is recorded.\n"},
                "brief": {"text": "A verification handoff for R1.\n"},
                "document": {"text": "# Draft\nThe draft covers R1.\n"},
                "coverage": {"text": "R1 is covered.\n"},
                "source:S1": {"text": "Policy first line.\nPolicy second line.\n"},
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    def response(self, *, returncode=0, stdout="", stderr=""):
        return type("Completed", (), {
            "returncode": returncode, "stdout": stdout, "stderr": stderr,
        })()

    def span_review(self):
        return {
            "schema_version": self.packet["schema_version"],
            "feature_key": self.packet["feature_key"],
            "stage": self.packet["stage"],
            "run_id": self.packet["run_id"],
            "input_sha256": self.packet["input_sha256"],
            "reviewer_id": self.packet["reviewer_id"],
            "source_obligations": [{
                "statement": "The source obligation is R1.",
                "requirement_ids": ["R1"],
                "evidence": [{"artifact": "source", "first_line": 2, "last_line": 2}],
            }],
            "requirements": [{
                "id": "R1", "status": "covered", "rationale": "The draft contains it.",
                "evidence": [{"artifact": "document", "first_line": 2, "last_line": 2}],
            }],
            "claims": [{
                "id": "C1", "status": "supported", "rationale": "The capture supports it.",
                "evidence": [{"artifact": "source:S1", "first_line": 1, "last_line": 2}],
            }],
            "findings": [{
                "severity": "minor", "description": "A minor note.",
                "evidence": [{"artifact": "document", "first_line": 1, "last_line": 1}],
            }],
            "owner_questions": [],
        }

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
        payload = {"structured_output": self.span_review()}
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
            expected_review = review_with_claude.resolve_review_spans(
                payload["structured_output"],
                review_with_claude.build_line_catalog(self.packet),
            )
            self.assertEqual(json.dumps(expected_review, ensure_ascii=False) + "\n", stdout)
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
            self.assertIn("evidence_catalog", json.loads(run.call_args.kwargs["input"]))
            system_prompt = command[command.index("--system-prompt") + 1]
            self.assertIn("first_line", system_prompt)
            self.assertIn("1-based and inclusive", system_prompt)

    def test_structured_output_is_extracted_and_packet_identity_is_schema_const(self):
        review = self.span_review()
        envelope = {"type": "result", "structured_output": review, "result": "discard me"}
        code, stdout, _, run, output = self.invoke("structured", self.response(stdout=json.dumps(envelope)))
        self.assertEqual(0, code)
        resolved = json.loads(stdout)
        self.assertNotEqual(review, resolved)
        self.assertEqual("Policy first line.\nPolicy second line.\n",
                         resolved["claims"][0]["evidence"][0]["quote"])
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
        self.assertEqual(list(self.packet["artifacts"]), requirement_item["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"])
        self.assertEqual(["supported", "unsupported", "unverified"],
                         claim_item["properties"]["status"]["enum"])
        self.assertEqual(list(self.packet["artifacts"]), claim_item["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"])
        self.assertEqual(["minor", "major", "blocking"],
                         finding_item["properties"]["severity"]["enum"])
        for item in (source_item, requirement_item, claim_item, finding_item):
            self.assertFalse(item["additionalProperties"])
            self.assertEqual(list(item["properties"]), item["required"])
        span_schema = requirement_item["properties"]["evidence"]["items"]
        self.assertEqual(["artifact", "first_line", "last_line"], span_schema["required"])
        self.assertNotIn("quote", span_schema["properties"])
        self.assertEqual({"type": "integer", "minimum": 1}, span_schema["properties"]["first_line"])
        self.assertEqual({"type": "integer", "minimum": 1}, span_schema["properties"]["last_line"])

        design_packet = {**self.packet, "stage": "design"}
        design_schema = review_with_claude.schema(design_packet)
        design_source_artifacts = design_schema["properties"]["source_obligations"]["items"]["properties"]["evidence"]["items"]["properties"]["artifact"]["enum"]
        self.assertEqual(["source", "approved_prd"], design_source_artifacts)

    def test_line_catalog_and_span_resolution_preserve_exact_multiline_text(self):
        packet = json.loads(json.dumps(self.packet))
        packet["artifacts"]["document"]["text"] = "first line\r\n  second line  \nthird line"
        catalog = review_with_claude.build_line_catalog(packet)
        document_lines = catalog["artifacts"]["document"]["lines"]
        self.assertEqual([
            {"line": 1, "text": "first line\r\n"},
            {"line": 2, "text": "  second line  \n"},
            {"line": 3, "text": "third line"},
        ], document_lines)
        self.assertEqual(packet["input_sha256"], catalog["input_sha256"])

        review = self.span_review()
        review["requirements"][0]["evidence"] = [{
            "artifact": "document", "first_line": 2, "last_line": 3,
        }]
        resolved = review_with_claude.resolve_review_spans(review, catalog)
        self.assertEqual("  second line  \nthird line",
                         resolved["requirements"][0]["evidence"][0]["quote"])
        self.assertEqual({"artifact", "quote"}, set(resolved["requirements"][0]["evidence"][0]))
        self.assertEqual({"artifact": "document", "first_line": 2, "last_line": 3},
                         review["requirements"][0]["evidence"][0])

    def test_span_resolution_rejects_unknown_out_of_bounds_reversed_bool_and_blank_ranges(self):
        catalog = review_with_claude.build_line_catalog(self.packet)
        cases = [
            ("unknown artifact", {"artifact": "missing", "first_line": 1, "last_line": 1}),
            ("past end", {"artifact": "document", "first_line": 1, "last_line": 99}),
            ("before start", {"artifact": "document", "first_line": 0, "last_line": 1}),
            ("reversed", {"artifact": "document", "first_line": 2, "last_line": 1}),
            ("boolean integer", {"artifact": "document", "first_line": True, "last_line": 1}),
            ("float integer", {"artifact": "document", "first_line": 1.0, "last_line": 1}),
            ("extra quote", {"artifact": "document", "first_line": 1, "last_line": 1, "quote": "repaired"}),
        ]
        for label, span in cases:
            with self.subTest(label=label):
                review = self.span_review()
                review["findings"][0]["evidence"] = [span]
                with self.assertRaises(ValueError):
                    review_with_claude.resolve_review_spans(review, catalog)

        review = self.span_review()
        review["findings"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "at least one"):
            review_with_claude.resolve_review_spans(review, catalog)

        blank_packet = json.loads(json.dumps(self.packet))
        blank_packet["artifacts"]["blank"] = {"text": " \t\n"}
        blank_catalog = review_with_claude.build_line_catalog(blank_packet)
        review = self.span_review()
        review["findings"][0]["evidence"] = [{
            "artifact": "blank", "first_line": 1, "last_line": 1,
        }]
        with self.assertRaisesRegex(ValueError, "blank text"):
            review_with_claude.resolve_review_spans(review, blank_catalog)

    def test_source_obligation_span_enforces_stage_scope_artifact_allowlist(self):
        prd_catalog = review_with_claude.build_line_catalog(self.packet)
        review = self.span_review()
        review["source_obligations"][0]["evidence"] = [{
            "artifact": "document", "first_line": 1, "last_line": 1,
        }]
        with self.assertRaisesRegex(ValueError, "invalid scope artifact"):
            review_with_claude.resolve_review_spans(review, prd_catalog)

        design_packet = json.loads(json.dumps(self.packet))
        design_packet["stage"] = "design"
        design_packet["artifacts"]["approved_prd"] = {"text": "Approved product scope.\n"}
        design_catalog = review_with_claude.build_line_catalog(design_packet)
        review = self.span_review()
        review["source_obligations"][0]["evidence"] = [{
            "artifact": "approved_prd", "first_line": 1, "last_line": 1,
        }]
        resolved = review_with_claude.resolve_review_spans(review, design_catalog)
        self.assertEqual("Approved product scope.\n",
                         resolved["source_obligations"][0]["evidence"][0]["quote"])

    def test_adapter_passes_sealed_packet_with_catalog_and_saves_raw_review_provenance(self):
        review = self.span_review()
        envelope = {"type": "result", "structured_output": review}
        code, stdout, _, run, output = self.invoke(
            "catalog-flow", self.response(stdout=json.dumps(envelope)),
        )
        self.assertEqual(0, code)
        model_input = json.loads(run.call_args.kwargs["input"])
        self.assertEqual(self.packet, model_input["packet"])
        self.assertEqual(self.packet["input_sha256"], model_input["packet"]["input_sha256"])
        catalog = model_input["evidence_catalog"]
        self.assertEqual(catalog, json.loads((output / "evidence-catalog.json").read_text()))
        self.assertEqual(2, catalog["artifacts"]["document"]["line_count"])
        self.assertEqual(review, json.loads((output / "structured-review.json").read_text()))
        provenance = json.loads((output / "provenance.json").read_text())
        self.assertEqual(self.packet["input_sha256"], provenance["input_sha256"])
        self.assertEqual("resolved", provenance["span_resolution"])
        self.assertTrue(provenance["structured_review_sha256"])
        self.assertTrue(provenance["resolved_review_sha256"])
        resolved = json.loads(stdout)
        self.assertEqual("The source obligation is R1.\n", resolved["source_obligations"][0]["evidence"][0]["quote"])
        self.assertEqual("The draft covers R1.\n", resolved["requirements"][0]["evidence"][0]["quote"])
        self.assertEqual("Policy first line.\nPolicy second line.\n", resolved["claims"][0]["evidence"][0]["quote"])
        self.assertEqual("# Draft\n", resolved["findings"][0]["evidence"][0]["quote"])
        for field in ("source_obligations", "requirements", "claims", "findings"):
            for row in resolved[field]:
                for reference in row["evidence"]:
                    self.assertEqual({"artifact", "quote"}, set(reference))

    def test_bad_span_fails_without_stdout_and_retains_raw_review_and_provenance(self):
        review = self.span_review()
        review["requirements"][0]["evidence"][0]["last_line"] = 100
        envelope = {"type": "result", "structured_output": review}
        code, stdout, stderr, _, output = self.invoke(
            "bad-span", self.response(stdout=json.dumps(envelope)),
        )
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertTrue(stderr.strip())
        self.assertEqual(review, json.loads((output / "structured-review.json").read_text()))
        provenance = json.loads((output / "provenance.json").read_text())
        self.assertEqual("failed", provenance["span_resolution"])
        self.assertEqual(review_with_claude.sha256_json(review), provenance["structured_review_sha256"])

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
